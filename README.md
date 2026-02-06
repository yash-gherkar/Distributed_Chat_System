Lowcost Lightweight Distributed Chat System
A robust, decentralized chat application designed with a focus on low-resource consumption and high fault tolerance. This system utilizes a peer-to-peer coordination model combined with a traditional client-server architecture to provide a reliable messaging platform without the need for expensive infrastructure.

1) Features
Dynamic Server Discovery: New nodes join the cluster automatically using UDP broadcasting, eliminating the need for hardcoded IP addresses.
Bully Election Algorithm: A hierarchy-based election process ensures that the server with the highest ID always assumes the leader role for coordination.
Failure Detection: Integrated heartbeat monitoring detects server or leader crashes within seconds, triggering automatic recovery.
Distributed Load Balancing: The leader dynamically assigns chatrooms to the server with the lowest current load to optimize performance.
Asynchronous Messaging: A multi-threaded client allows users to receive messages in real-time without interrupting their current typing line.
Lightweight Communication: All system coordination and messaging are performed over best-effort UDP to minimize overhead.

2) Architecture
The system consists of three main components:
The Leader: A server elected by the cluster to manage "global" state, such as room assignments and the global client directory.
The Follower: Active servers that handle direct socket connections with clients while coordinating with the leader for load balancing.
The Client: The end-user interface that discovers available servers via broadcast and joins chatrooms.

3) Technologies Used
Python 3.x: Core logic and networking.
Socket Programming: UDP (User Datagram Protocol) for high-speed, low-latency communication.
Threading: For handling concurrent tasks like heartbeats, elections, and message listening.
JSON: Lightweight data serialization for all network packets.

4) Setup and Installation
   
Clone the repository:

Bash
git clone https://github.com/your-username/Distributed_Chat_System.git
cd Distributed_Chat_System

Ensure you have Python 3 installed:

Bash
python3 --version


🚥 How to Run

1. Start the Servers
Open multiple terminal windows to create a cluster. The first server will become the leader, and subsequent servers with higher IDs will "bully" their way into leadership.

Server 1 (Port 5001):
Bash
python3 server.py --id 1 --port 5001

Server 2 (Port 5002):
Bash
python3 server.py --id 2 --port 5002

2. Start the Clients
Open new terminals to run the clients. They will automatically search for the servers on the network.

For manually adding - python3 client.py --server_ip 100.64.156.17 --server_port 5002

Bash
python3 client.py
Enter a Client ID (e.g., Alice).
Follow the prompts to Create or Join a room.

⚠️ Current Constraints
In-Memory Only: To remain lightweight, all state (rooms, assignments) is stored in RAM and is reset if the cluster restarts.
Best-Effort Delivery: Uses UDP without custom acknowledgments; it prioritizes speed over 100% message reliability in high-loss environments.

🔮 Future Work
Persistent Storage: Implementing a JSON-based log to allow state recovery after a total system reboot.
State Reconciliation: Adding a handshake for new leaders to "learn" room assignments from followers after an election.
Encryption: Adding basic TLS/SSL wrappers for secure messaging.

This project was developed as part of a distributed systems course at the University of Stuttgart.
