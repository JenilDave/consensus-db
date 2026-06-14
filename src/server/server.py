import sys
import os
import grpc
from concurrent import futures
import logging
import json
import threading
import time

# Ensure src and proto are in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'proto')))

import kvstore_pb2
import kvstore_pb2_grpc
from src.storage.base import BaseStorage
from src.storage.durable import DurableStorage

class ConfigManager:
    def __init__(self, config_file, my_port):
        self.config_file = config_file
        self.my_port = my_port
        self.role = "follower"
        self.follower_stubs = []
        self.leader_stub = None
        self._last_mtime = 0
        self.lock = threading.Lock()
        
        self.load_config()
        self.watch_thread = threading.Thread(target=self._watch_config, daemon=True)
        self.watch_thread.start()

    def _watch_config(self):
        while True:
            time.sleep(1)
            try:
                mtime = os.path.getmtime(self.config_file)
                if mtime > self._last_mtime:
                    logging.info("Configuration change detected! Hot-reloading...")
                    self.load_config()
                    self._last_mtime = mtime
            except Exception:
                pass

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            with self.lock:
                leader_port = config.get("leader_port")
                all_cluster_ports = config.get("cluster_ports", [])
                
                if leader_port is not None and self.my_port == leader_port:
                    if self.role != "primary":
                        logging.info(f"Node on port {self.my_port} became LEADER.")
                    self.role = "primary"
                    
                    new_stubs = []
                    for p in all_cluster_ports:
                        if p != self.my_port:
                            channel = grpc.insecure_channel(f"localhost:{p}")
                            new_stubs.append(kvstore_pb2_grpc.KeyValueStoreStub(channel))
                    self.follower_stubs = new_stubs
                    self.leader_stub = None
                else:
                    if self.role != "follower":
                        logging.info(f"Node on port {self.my_port} became FOLLOWER.")
                    self.role = "follower"
                    self.follower_stubs = []
                    if leader_port is not None:
                        channel = grpc.insecure_channel(f"localhost:{leader_port}")
                        self.leader_stub = kvstore_pb2_grpc.KeyValueStoreStub(channel)
                    else:
                        self.leader_stub = None
        except Exception as e:
            logging.error(f"Error loading config: {e}")

class KeyValueStoreServicer(kvstore_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, storage: DurableStorage, config_manager: ConfigManager):
        self.storage = storage
        self.config_manager = config_manager
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def _heartbeat_loop(self):
        while True:
            time.sleep(2)
            if self.config_manager.role == "primary":
                with self.storage._lock:
                    commit_id = self.storage.commit_id
                    term_id = self.storage.term_id
                
                req = kvstore_pb2.HeartbeatRequest(
                    term_id=term_id,
                    commit_id=commit_id,
                    leader_port=self.config_manager.my_port
                )
                
                with self.config_manager.lock:
                    stubs = list(self.config_manager.follower_stubs)
                    
                for stub in stubs:
                    try:
                        stub.Heartbeat(req, timeout=1)
                    except grpc.RpcError:
                        pass # Follower might be offline or busy

    def Put(self, request, context):
        is_leader = (self.config_manager.role == "primary")
        
        if is_leader:
            with self.storage._lock:
                self.storage.commit_id += 1
                commit_id = self.storage.commit_id
                term_id = self.storage.term_id
            
            success = self.storage.put_with_ids(request.key, request.value, commit_id, term_id)
            
            repl_request = kvstore_pb2.PutRequest(
                key=request.key, 
                value=request.value, 
                commit_id=commit_id, 
                term_id=term_id
            )
            
            if success:
                with self.config_manager.lock:
                    stubs = list(self.config_manager.follower_stubs)
                    
                for stub in stubs:
                    try:
                        stub.Put(repl_request)
                    except grpc.RpcError as e:
                        logging.error(f"Failed to replicate Put to follower: {e}")
            return kvstore_pb2.PutResponse(success=success, message="Value stored successfully.")
        else:
            if request.commit_id == 0:
                with self.config_manager.lock:
                    leader_stub = self.config_manager.leader_stub
                if leader_stub:
                    try:
                        return leader_stub.Put(request)
                    except grpc.RpcError as e:
                        return kvstore_pb2.PutResponse(success=False, message=f"Failed to forward to leader: {e}")
                else:
                    return kvstore_pb2.PutResponse(success=False, message="No leader elected yet.")
            else:
                success = self.storage.put_with_ids(request.key, request.value, request.commit_id, request.term_id)
                return kvstore_pb2.PutResponse(success=success, message="Value stored successfully.")

    def Get(self, request, context):
        value = self.storage.get(request.key)
        if value is not None:
            return kvstore_pb2.GetResponse(found=True, value=value)
        else:
            return kvstore_pb2.GetResponse(found=False, value="")

    def Delete(self, request, context):
        is_leader = (self.config_manager.role == "primary")
        
        if is_leader:
            with self.storage._lock:
                self.storage.commit_id += 1
                commit_id = self.storage.commit_id
                term_id = self.storage.term_id
                
            success = self.storage.delete_with_ids(request.key, commit_id, term_id)
            
            repl_request = kvstore_pb2.DeleteRequest(
                key=request.key,
                commit_id=commit_id,
                term_id=term_id
            )
            
            if success:
                with self.config_manager.lock:
                    stubs = list(self.config_manager.follower_stubs)
                    
                for stub in stubs:
                    try:
                        stub.Delete(repl_request)
                    except grpc.RpcError as e:
                        logging.error(f"Failed to replicate Delete to follower: {e}")
            return kvstore_pb2.DeleteResponse(success=success, message="Key deleted successfully.")
        else:
            if request.commit_id == 0:
                with self.config_manager.lock:
                    leader_stub = self.config_manager.leader_stub
                if leader_stub:
                    try:
                        return leader_stub.Delete(request)
                    except grpc.RpcError as e:
                        return kvstore_pb2.DeleteResponse(success=False, message=f"Failed to forward to leader: {e}")
                else:
                    return kvstore_pb2.DeleteResponse(success=False, message="No leader elected yet.")
            else:
                success = self.storage.delete_with_ids(request.key, request.commit_id, request.term_id)
                return kvstore_pb2.DeleteResponse(success=success, message="Key deleted successfully.")

    def SyncLogs(self, request, context):
        entries = self.storage.get_logs_since(request.from_commit_id)
        pb_entries = []
        for e in entries:
            pb_entries.append(kvstore_pb2.SyncEntry(
                op=e.get("op", ""),
                key=e.get("key", ""),
                value=e.get("value", "") if e.get("value") is not None else "",
                commit_id=e.get("commit_id", 0),
                term_id=e.get("term_id", 1)
            ))
        return kvstore_pb2.SyncResponse(entries=pb_entries)

    def Heartbeat(self, request, context):
        with self.storage._lock:
            local_commit = self.storage.commit_id
            
        if request.commit_id > local_commit:
            threading.Thread(target=self._trigger_sync, args=(local_commit,), daemon=True).start()
            
        return kvstore_pb2.HeartbeatResponse(success=True)

    def _trigger_sync(self, local_commit):
        with self.config_manager.lock:
            leader_stub = self.config_manager.leader_stub
            
        if leader_stub:
            logging.info(f"Heartbeat: Log is outdated! Syncing from leader starting from commit {local_commit}...")
            try:
                req = kvstore_pb2.SyncRequest(from_commit_id=local_commit)
                resp = leader_stub.SyncLogs(req)
                for entry in resp.entries:
                    if entry.op == "put":
                        self.storage.put_with_ids(entry.key, entry.value, entry.commit_id, entry.term_id)
                    elif entry.op == "delete":
                        self.storage.delete_with_ids(entry.key, entry.commit_id, entry.term_id)
                if resp.entries:
                    logging.info(f"Successfully caught up {len(resp.entries)} missing logs from leader.")
            except Exception as e:
                logging.error(f"Failed to sync logs from leader during heartbeat catch-up: {e}")

def run_server():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    config_file = 'cluster.json'
    
    if not os.path.exists(config_file):
        logging.error(f"Configuration file {config_file} not found. Please create it.")
        sys.exit(1)

    with open(config_file, 'r') as f:
        config = json.load(f)

    ports_to_try = config.get("cluster_ports", [])
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    bound_port = 0
    
    # Auto-bind to figure out who we are
    for p in ports_to_try:
        if not p: continue
        try:
            port_result = server.add_insecure_port(f'[::]:{p}')
            if port_result != 0:
                bound_port = p
                break
        except RuntimeError:
            continue
            
    if bound_port == 0:
        logging.error("Could not bind to any port listed in cluster.json. Is the cluster already full?")
        sys.exit(1)
        
    logging.info(f"Successfully bound to port {bound_port}.")
    
    storage_engine = DurableStorage(bound_port)
    config_manager = ConfigManager(config_file, bound_port)
    
    # Catch-up mechanism on startup
    with config_manager.lock:
        leader_stub = config_manager.leader_stub
        
    if leader_stub:
        logging.info(f"Syncing logs from leader starting from local commit {storage_engine.commit_id}...")
        try:
            req = kvstore_pb2.SyncRequest(from_commit_id=storage_engine.commit_id)
            resp = leader_stub.SyncLogs(req)
            for entry in resp.entries:
                if entry.op == "put":
                    storage_engine.put_with_ids(entry.key, entry.value, entry.commit_id, entry.term_id)
                elif entry.op == "delete":
                    storage_engine.delete_with_ids(entry.key, entry.commit_id, entry.term_id)
            if resp.entries:
                logging.info(f"Successfully caught up {len(resp.entries)} missing logs from leader.")
            else:
                logging.info("Local log is already fully up-to-date with leader.")
        except Exception as e:
            logging.error(f"Failed to sync logs from leader: {e}")
    
    kvstore_pb2_grpc.add_KeyValueStoreServicer_to_server(KeyValueStoreServicer(storage_engine, config_manager), server)
    
    server.start()
    logging.info(f"Server is running on port {bound_port} as {config_manager.role.upper()}")
    server.wait_for_termination()

if __name__ == '__main__':
    run_server()
