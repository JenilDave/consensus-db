# Consensus DB

A modular, gRPC-based Key-Value Store built in Python. Features dynamic cluster auto-discovery, hot-reloading configurations, and primary/follower replication.

## Features
- **gRPC API**: Fast and robust protocol buffers based communication.
- **Dynamic Port Binding**: Nodes auto-discover their identity on startup based on available ports defined in a single configuration file.
- **Hot-Reloading Configuration**: Update the cluster topology (like electing a new leader) during runtime. The servers detect the change instantly without needing a restart.
- **Replication**: The leader node automatically forwards `Put` and `Delete` requests to all follower nodes.
- **Write Forwarding**: Clients can send write requests to any follower node, which will transparently proxy them to the leader to ensure single-source-of-truth ordering.
- **Leader Heartbeats**: The leader broadcasts background heartbeat RPCs to all followers every 2 seconds to announce its presence and its latest commit index.
- **Quorum Consensus**: The leader utilizes a two-phase-like approach for writes. It broadcasts the write to followers in parallel and will only commit the transaction locally if it receives successful acknowledgments from a majority (>50%) of the cluster. If quorum is not met, the write is aborted.
- **Durability (Write-Ahead Log)**: Operations are durably persisted to a local `.jsonl` file per node. If a node crashes, it perfectly rebuilds its dictionary state and commit ID upon restart.
- **Automatic Failure Recovery (SyncLogs RPC)**: When a node boots up, it reads its local WAL and then automatically queries the leader for any logs it missed while offline, bringing itself instantly up to speed before accepting client requests.
- **Client Auto-Discovery**: The client integration script automatically parses `cluster.json` to route directly to the active leader port without hardcoding.

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
*(Note: The client will automatically discover the leader by reading `cluster.json`!)*

### 4. Test Failure Recovery
1. Run each node in its own terminal using `uv run python src/server/server.py`.
2. Kill one of the follower terminals (`Ctrl+C`).
3. Run the client script to create new data on the leader.
4. Restart the dead follower terminal. Watch it automatically rebuild its historical state from its `data_{port}.jsonl` file and trigger a `SyncLogs` RPC to fetch the missing writes from the leader!
