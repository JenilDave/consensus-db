import sys
import os
import grpc
import logging

# Ensure src and proto are in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'proto')))

import kvstore_pb2
import kvstore_pb2_grpc

class KeyValueClient:
    def __init__(self, host: str = 'localhost', port: int = 50052):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = kvstore_pb2_grpc.KeyValueStoreStub(self.channel)

    def put(self, key: str, value: str) -> bool:
        request = kvstore_pb2.PutRequest(key=key, value=value)
        response = self.stub.Put(request)
        return response.success

    def get(self, key: str) -> str:
        request = kvstore_pb2.GetRequest(key=key)
        response = self.stub.Get(request)
        if response.found:
            return response.value
        return None

    def delete(self, key: str) -> bool:
        request = kvstore_pb2.DeleteRequest(key=key)
        response = self.stub.Delete(request)
        return response.success

    def close(self):
        self.channel.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    client = KeyValueClient()
    
    print("Putting 'name3' = 'db'")
    success = client.put("name3", "db")
    print(f"Put success: {success}")
    
    print("\nGetting 'name3'")
    value = client.get("name3")
    print(f"Got value: {value}")
    
    print("\nDeleting 'name3'")
    success = client.delete("name3")
    print(f"Delete success: {success}")
    
    print("\nGetting 'name3' again")
    value = client.get("name3")
    print(f"Got value: {value}")

    client.close()
