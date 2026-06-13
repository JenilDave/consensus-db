# Consensus DB

A modular, gRPC-based Key-Value Store built in Python. Features dynamic cluster auto-discovery, hot-reloading configurations, and primary/follower replication.

## Features
- **gRPC API**: Fast and robust protocol buffers based communication.
- **Dynamic Port Binding**: Nodes auto-discover their identity on startup based on available ports defined in a single configuration file.
- **Hot-Reloading Configuration**: Update the cluster topology (like electing a new leader) during runtime. The servers detect the change instantly without needing a restart.
- **Replication**: The leader node automatically forwards `Put` and `Delete` requests to all follower nodes.
- **Modular Storage**: Easily swap the default in-memory dictionary backend for disk-persistence or caching engines.

## Prerequisites
- [uv](https://docs.astral.sh/uv/) (Python packaging and project manager)
- Python 3.12+

## Installation Guide

1. Clone the repository.
2. Ensure you have `uv` installed.
3. Install dependencies and set up the virtual environment:
   ```bash
   uv sync
   ```
*(Alternatively, you can just rely on `uv run` which handles the virtual environment and installs dependencies automatically).*

## Configuration
The entire cluster is managed by a single `cluster.json` file in the root directory:
```json
{
    "leader_port": null,
    "cluster_ports": [
        50051,
        50052,
        50053
    ]
}
```
- `cluster_ports`: List of ports the nodes are allowed to bind to. When a node starts, it iterates through the list and binds to the first available port.
- `leader_port`: Determines which port acts as the Primary/Leader. If set to `null`, all nodes default to Follower mode.

## How to Run

### 1. Start the Cluster
You can spin up all the nodes simultaneously with the cluster runner script:
```powershell
uv run python start_cluster.py
```
*This will boot up identical nodes based on the size of the `cluster_ports` array. By default, they will all start as Followers.*

### 2. Dynamically Elect a Leader
While the cluster is running, open `cluster.json` and change the `"leader_port"` to one of the active ports, e.g., `50051`.
Save the file.
You will immediately see the node on `50051` log that it became the LEADER, dynamically establishing gRPC connections to the other follower nodes.

### 3. Run the Client
Once a leader is elected, you can run the integration test client to verify `Put`, `Get`, and `Delete` replication:
```powershell
uv run python src/client/client.py
```
*(Note: The default client script connects to port 50051).*
