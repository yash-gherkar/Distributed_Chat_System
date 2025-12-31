
# server/server.py
import socket
import json
import threading
import time
import argparse

from protocol import *
from state import ServerState
from heartbeat import HeartbeatManager
from election import ElectionManager

BUFFER_SIZE = 4096


class Server:
    def __init__(self, server_id, port):
        self.state = ServerState(server_id)

        self.addr = ("127.0.0.1", port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.addr)

        self.heartbeat = HeartbeatManager(self)
        self.election = ElectionManager(self)

        # leader initializes itself
        self.state.servers[server_id] = self.addr
        self.state.server_load[server_id] = 0

        print(f"[START] Server {server_id} on port {port}")

    # ---------------- Networking ----------------

    def send(self, addr, msg):
        self.sock.sendto(json.dumps(msg).encode(), addr)

    def receive_loop(self):
        while True:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            msg = json.loads(data.decode())
            self.handle_message(msg, addr)

    # ---------------- Dispatcher ----------------

    def handle_message(self, msg, addr):
        t = msg["type"]

        if t == SERVER_UP:
            self.handle_server_up(msg, addr)

        elif t == STATE_SYNC:
            self.handle_state_sync(msg)

        elif t == CLIENT_JOIN:
            self.handle_client_join(msg, addr)

        elif t == LIST_CHATROOMS:
            self.send(addr, {
                "type": CHATROOMS_LIST,
                "rooms": list(self.state.chatrooms.keys())
            })

        elif t == CREATE_CHATROOM:
            self.handle_create_chatroom(msg, addr)

        elif t == JOIN_CHATROOM:
            self.handle_join_chatroom(msg, addr)

        elif t == ROOM_ASSIGNMENT_UPDATE:
            self.handle_room_update(msg)

        elif t == CHAT_MSG:
            self.handle_chat_message(msg)

        elif t == ACK:
            self.handle_ack(msg)

        elif t == HEARTBEAT:
            self.state.last_heartbeat = time.time()

        elif t == LEADER_ANNOUNCE:
            self.state.is_leader = (msg["leader_id"] == self.state.server_id)
            self.state.leader_addr = addr
            print(f"[LEADER] New leader {msg['leader_id']}")

    # ---------------- Server Join ----------------

    def handle_server_up(self, msg, addr):
        if not self.state.is_leader:
            return

        sid = msg["server_id"]
        self.state.servers[sid] = addr
        self.state.server_load[sid] = 0

        self.send(addr, {
            "type": STATE_SYNC,
            "chatrooms": self.state.chatrooms,
            "server_load": self.state.server_load
        })

        print(f"[SERVER] Server {sid} joined cluster")

    def handle_state_sync(self, msg):
        self.state.chatrooms = msg["chatrooms"]
        self.state.server_load = msg["server_load"]
        print("[SYNC] State synchronized")

    # ---------------- Client Logic ----------------

    def handle_client_join(self, msg, addr):
        self.state.clients[msg["client_id"]] = addr

        # always reply with chatroom list
        self.send(addr, {
            "type": CHATROOMS_LIST,
            "rooms": list(self.state.chatrooms.keys())
        })

    def handle_create_chatroom(self, msg, addr):
        room = msg["room"]

        # leader assigns least-loaded server
        target = min(self.state.server_load, key=self.state.server_load.get)
        self.state.chatrooms[room] = target
        self.state.server_load[target] += 1

        # broadcast assignment
        for saddr in self.state.servers.values():
            self.send(saddr, {
                "type": ROOM_ASSIGNMENT_UPDATE,
                "room": room,
                "server_id": target
            })

        # tell client
        self.send(addr, {
            "type": ROOM_ASSIGNMENT,
            "room": room,
            "server_addr": self.state.servers[target]
        })

        print(f"[ROOM] '{room}' assigned to Server {target}")

    def handle_join_chatroom(self, msg, addr):
        room = msg["room"]
        owner = self.state.chatrooms[room]

        self.send(addr, {
            "type": ROOM_ASSIGNMENT,
            "room": room,
            "server_addr": self.state.servers[owner]
        })

    def handle_room_update(self, msg):
        room = msg["room"]
        sid = msg["server_id"]

        self.state.chatrooms[room] = sid
        if sid == self.state.server_id:
            self.state.local_rooms.setdefault(room, set())

        print(f"[UPDATE] Room '{room}' owned by Server {sid}")

    # ---------------- Chat ----------------

    def handle_chat_message(self, msg):
        room = msg["room"]
        sender = msg["from"]

        if room not in self.state.local_rooms:
            return

        print(f"[ROOM {room}] {sender}: {msg['body']}")

        for cid, addr in self.state.clients.items():
            self.send(addr, msg)

    def handle_ack(self, msg):
        pass  # simplified for demo


# ---------------- Main ----------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    server = Server(args.id, args.port)

    if args.id == 1:
        server.state.is_leader = True
        server.state.leader_addr = server.addr
        print("[LEADER] I am the leader")

    else:
        server.send(("127.0.0.1", 5001), {
            "type": SERVER_UP,
            "server_id": args.id
        })

    server.heartbeat.start()
    server.receive_loop()
