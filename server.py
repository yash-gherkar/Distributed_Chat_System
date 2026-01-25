import socket
import threading
import json
import time
import uuid
import argparse
import ipaddress
from protocol import *

BUFFER_SIZE = 4096
HEARTBEAT_INTERVAL = 2
HEARTBEAT_TIMEOUT = 6
DISCOVERY_PORT = 5000  # fixed discovery port for LAN broadcast

class ServerState:
    def __init__(self, server_id, addr):
        self.server_id = server_id
        self.addr = addr
        self.is_leader = False
        self.leader_addr = None
        self.participant = False  # for ring election

class Server:
    def __init__(self, server_id, port):
        self.state = ServerState(server_id, ('', port))
        self.port = port
        self.addr = ('', port)

        # Networking
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.addr)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Chatroom state
        self.servers = {}  # server_id -> (ip, port)
        self.clients = {}  # client_id -> (ip, port)
        self.chatrooms = {}  # room -> list of client_ids
        self.room_assignment = {}  # room -> server_id

        self.last_heartbeat = time.time()

        # Threads
        threading.Thread(target=self.receive_loop, daemon=True).start()
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        threading.Thread(target=self.discovery_loop, daemon=True).start()
        threading.Thread(target=self.election_loop, daemon=True).start()

    # -------------------- Networking --------------------
    def send(self, addr, msg):
        self.sock.sendto(json.dumps(msg).encode(), addr)

    def broadcast_to_servers(self, msg):
        for s_addr in self.servers.values():
            self.send(s_addr, msg)

    # -------------------- Loops --------------------
    def receive_loop(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                self.handle_message(msg, addr)
            except Exception as e:
                print("[RECV ERROR]", e)

    def heartbeat_loop(self):
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            if self.state.is_leader:
                # Leader sends heartbeat to other servers
                self.broadcast_to_servers({"type": HEARTBEAT, "from": self.state.server_id})
            else:
                if time.time() - self.last_heartbeat > HEARTBEAT_TIMEOUT:
                    print("[ELECTION] Leader timeout, starting ring election")
                    self.start_election()

    def discovery_loop(self):
        """Listen on DISCOVERY_PORT for client discovery"""
        discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_sock.bind(('', DISCOVERY_PORT))
        discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            try:
                data, addr = discovery_sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                if msg.get("type") == DISCOVER_SERVER:
                    self.send(addr, {
                        "type": SERVER_ADVERTISEMENT,
                        "server_id": self.state.server_id,
                        "addr": self.addr,
                        "is_leader": self.state.is_leader
                    })
            except:
                pass

    def election_loop(self):
        # Ring election placeholder, can implement ring logic
        while True:
            time.sleep(1)

    # -------------------- Election --------------------
    def start_election(self):
        # Simple highest-ID election for demo
        all_ids = list(self.servers.keys()) + [self.state.server_id]
        new_leader_id = max(all_ids)
        self.state.is_leader = (new_leader_id == self.state.server_id)
        self.state.leader_addr = self.servers.get(new_leader_id, self.addr)
        print(f"[ELECTION] New leader: {new_leader_id}, I am leader: {self.state.is_leader}")

    # -------------------- Message Handling --------------------
    def handle_message(self, msg, addr):
        t = msg.get("type")
        if t == CLIENT_JOIN:
            client_id = msg["client_id"]
            self.clients[client_id] = addr
            self.send(addr, {"type": CHATROOMS_LIST, "rooms": list(self.chatrooms.keys())})

        elif t == CREATE_CHATROOM:
            room = msg["room"]
            client_id = msg["client_id"]
            # Leader decides server assignment
            server_for_room = self.choose_server_for_room()
            self.chatrooms[room] = [client_id]
            self.room_assignment[room] = server_for_room[1]  # server port
            self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": server_for_room})

        elif t == JOIN_CHATROOM:
            room = msg["room"]
            client_id = msg["client_id"]
            if room in self.chatrooms:
                self.chatrooms[room].append(client_id)
            else:
                self.chatrooms[room] = [client_id]
            self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": self.addr})

        elif t == CHAT_MSG:
            room = msg["room"]
            if room in self.chatrooms:
                for cid in self.chatrooms[room]:
                    if cid != msg["from"]:
                        client_addr = self.clients.get(cid)
                        if client_addr:
                            self.send(client_addr, msg)

        elif t == HEARTBEAT:
            self.last_heartbeat = time.time()

    # -------------------- Load balancing --------------------
    def choose_server_for_room(self):
        """Leader picks the least-loaded server (or self if alone)"""
        if not self.servers:
            return self.addr
        load_map = {sid: 0 for sid in self.servers}
        for r_clients in self.chatrooms.values():
            for cid in r_clients:
                # Count clients per server (simplified)
                server_port = self.room_assignment.get(r_clients, self.port)
                load_map[server_port] = load_map.get(server_port, 0) + 1
        # Choose server with least clients
        min_server_port = min(load_map, key=load_map.get)
        for sid, addr in self.servers.items():
            if addr[1] == min_server_port:
                return addr
        return self.addr  # fallback

# -------------------- Main --------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()

    server = Server(args.id, args.port)
    print(f"Server {args.id} running on port {args.port}")

    while True:
        time.sleep(1)
