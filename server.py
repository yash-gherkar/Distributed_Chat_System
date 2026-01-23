import socket
import threading
import json
import time
import uuid
import argparse
from protocol import *

BUFFER_SIZE = 4096
HEARTBEAT_INTERVAL = 2
HEARTBEAT_TIMEOUT = 6

class Server:
    def __init__(self, server_id, port):
        self.id = server_id
        self.port = port
        self.addr = ('', port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.addr)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Server state
        self.is_leader = False
        self.leader_addr = None
        self.servers = {}  # server_id -> (ip, port)
        self.clients = {}  # client_id -> (ip, port)
        self.chatrooms = {}  # room -> list of client_ids
        self.room_assignment = {}  # room -> server_id

        self.last_heartbeat = time.time()

        # Start threads
        threading.Thread(target=self.receive_loop, daemon=True).start()
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        threading.Thread(target=self.election_loop, daemon=True).start()

    def send(self, addr, msg):
        self.sock.sendto(json.dumps(msg).encode(), addr)

    def broadcast(self, msg):
        for s_id, addr in self.servers.items():
            self.send(addr, msg)

    def receive_loop(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                self.handle_message(msg, addr)
            except Exception as e:
                print("Receive error:", e)

    def heartbeat_loop(self):
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            if self.is_leader:
                self.broadcast({"type": HEARTBEAT, "from": self.id})
            else:
                if time.time() - self.last_heartbeat > HEARTBEAT_TIMEOUT:
                    print("Leader timeout detected, starting election")
                    self.start_election()

    def election_loop(self):
        # Only waits for election messages
        while True:
            time.sleep(1)

    def start_election(self):
        all_ids = list(self.servers.keys()) + [self.id]
        new_leader = max(all_ids)
        self.leader_addr = self.servers.get(new_leader, self.addr)
        self.is_leader = (new_leader == self.id)
        print(f"New leader elected: {new_leader}, I am leader: {self.is_leader}")

    def handle_message(self, msg, addr):
        t = msg.get("type")

        if t == CLIENT_JOIN:
            client_id = msg["client_id"]
            self.clients[client_id] = addr
            # Send chatroom list
            self.send(addr, {"type": CHATROOMS_LIST, "rooms": list(self.chatrooms.keys())})

        elif t == CREATE_CHATROOM:
            room = msg["room"]
            client_id = msg["client_id"]
            self.chatrooms[room] = [client_id]
            self.room_assignment[room] = self.id
            self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": self.addr})

        elif t == JOIN_CHATROOM:
            room = msg["room"]
            client_id = msg["client_id"]
            if room in self.chatrooms:
                self.chatrooms[room].append(client_id)
            else:
                self.chatrooms[room] = [client_id]
            self.room_assignment[room] = self.id
            self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": self.addr})

        elif t == CHAT_MSG:
            room = msg["room"]
            if room in self.chatrooms:
                for client_id in self.chatrooms[room]:
                    if client_id != msg["from"]:
                        client_addr = self.clients.get(client_id)
                        if client_addr:
                            self.send(client_addr, msg)

        elif t == HEARTBEAT:
            self.last_heartbeat = time.time()

        elif t == DISCOVER_SERVER:
            self.send(addr, {
                "type": SERVER_ADVERTISEMENT,
                "server_id": self.id,
                "addr": self.addr,
                "is_leader": self.is_leader
            })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()

    server = Server(args.id, args.port)
    print(f"Server {args.id} running on port {args.port}")

    while True:
        time.sleep(1)