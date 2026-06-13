import json
import subprocess
import time
import sys
import os

def main():
    config_file = 'cluster.json'
    if not os.path.exists(config_file):
        print(f"Failed to find {config_file}")
        sys.exit(1)
        
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Failed to load cluster.json: {e}")
        sys.exit(1)
        
    num_nodes = len(config.get("cluster_ports", []))
    total_nodes = num_nodes
    
    print(f"Starting cluster with {total_nodes} nodes (All starting as followers)...")
    
    processes = []
    
    try:
        for i in range(total_nodes):
            print(f"Spawning node {i+1}...")
            # Use subprocess to start the server instances
            p = subprocess.Popen(
                ["uv", "run", "python", "src/server/server.py"]
            )
            processes.append(p)
            # Small delay to ensure they bind ports sequentially
            time.sleep(1)
            
        print("\n=== All cluster nodes started successfully! ===")
        print("Press Ctrl+C at any time to shut down the entire cluster.\n")
        
        # Keep the main script alive while children run
        for p in processes:
            p.wait()
            
    except KeyboardInterrupt:
        print("\n[Shutting down cluster...]")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("Cluster stopped completely.")

if __name__ == '__main__':
    main()
