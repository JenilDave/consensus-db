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
from src.storage.memory import MemoryStorage

class ConfigManager:
    def __init__(self, config_file, my_port):
        self.config_file = config_file
        self.my_port = my_port
        self.role = "follower"
        self.follower_stubs = []
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
                else:
                    if self.role != "follower":
                        logging.info(f"Node on port {self.my_port} became FOLLOWER.")
                    self.role = "follower"
                    self.follower_stubs = []
        except Exception as e:
            logging.error(f"Error loading config: {e}")

class KeyValueStoreServicer(kvstore_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, storage: BaseStorage, config_manager: ConfigManager):
        self.storage = storage
        self.config_manager = config_manager

    def Put(self, request, context):
        success = self.storage.put(request.key, request.value)
        
        if success:
            with self.config_manager.lock:
                stubs = list(self.config_manager.follower_stubs)
                
            for stub in stubs:
                try:
                    stub.Put(request)
                except grpc.RpcError as e:
                    logging.error(f"Failed to replicate Put to follower: {e}")
                
        return kvstore_pb2.PutResponse(success=success, message="Value stored successfully.")

    def Get(self, request, context):
        value = self.storage.get(request.key)
        if value is not None:
            return kvstore_pb2.GetResponse(found=True, value=value)
        else:
            return kvstore_pb2.GetResponse(found=False, value="")

    def Delete(self, request, context):
        success = self.storage.delete(request.key)
        
        if success:
            with self.config_manager.lock:
                stubs = list(self.config_manager.follower_stubs)
                
            for stub in stubs:
                try:
                    stub.Delete(request)
                except grpc.RpcError as e:
                    logging.error(f"Failed to replicate Delete to follower: {e}")
                
        if success:
            return kvstore_pb2.DeleteResponse(success=True, message="Key deleted successfully.")
        else:
            return kvstore_pb2.DeleteResponse(success=False, message="Key not found.")

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
    
    storage_engine = MemoryStorage()
    config_manager = ConfigManager(config_file, bound_port)
    
    kvstore_pb2_grpc.add_KeyValueStoreServicer_to_server(KeyValueStoreServicer(storage_engine, config_manager), server)
    
    server.start()
    logging.info(f"Server is running on port {bound_port} as {config_manager.role.upper()}")
    server.wait_for_termination()

if __name__ == '__main__':
    run_server()
