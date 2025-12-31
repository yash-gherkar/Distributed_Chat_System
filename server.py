# server/server.py
import socket
import json
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

        # register self
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

        if t == SERVER_UP and self.state.is_leader:
            sid = msg["server_id"]
            self.state.servers[sid] = addr
            self.state.server_load[sid] = 0

            self.send(addr, {
                "type": STATE_SYNC,
                "chatrooms": self.state.chatrooms,
                "server_load": self.state.server_load,
                "leader_id": self.state.server_id,
                "leader_addr": self.addr
            })

            print(f"[SERVER] Server {sid} joined")

        elif t == STATE_SYNC:
            self.state.chatrooms = msg["chatrooms"]
            self.state.server_load = msg["server_load"]

            self.state.leader_id = msg["leader_id"]
            self.state.leader_addr = tuple(msg["leader_addr"])

            # re-register self
            self.state.servers[self.state.server_id] = self.addr

            print("[SYNC] State synchronized")

        elif t == LEADER_ANNOUNCE:
            self.state.leader_id = msg["leader_id"]
            self.state.is_leader = (msg["leader_id"] == self.state.server_id)
            self.state.leader_addr = addr
            print(f"[LEADER] Leader is {msg['leader_id']}")

        elif t == HEARTBEAT:
            self.state.last_heartbeat = time.time()

        elif t == CLIENT_JOIN:
            self.state.clients[msg["client_id"]] = addr
            self.send(addr, {
                "type": CHATROOMS_LIST,
                "rooms": list(self.state.chatrooms.keys())
            })

        elif t in (CREATE_CHATROOM, JOIN_CHATROOM):
            self._handle_room_request(msg, addr)

        elif t == ROOM_ASSIGNMENT_UPDATE:
            room = msg["room"]
            sid = msg["server_id"]
            self.state.chatrooms[room] = sid

            if sid == self.state.server_id:
                self.state.local_rooms.setdefault(room, set())

            print(f"[ROOM] {room} hosted by server {sid}")

        elif t == CHAT_MSG:
            room = msg["room"]
            if room not in self.state.local_rooms:
                return

            for caddr in self.state.clients.values():
                self.send(caddr, msg)

    # ---------------- Room Handling ----------------

    def _handle_room_request(self, msg, addr):
        if not self.state.is_leader:
            self.send(self.state.leader_addr, msg)
            return

        room = msg["room"]

        if room not in self.state.chatrooms:
            target = min(self.state.server_load, key=self.state.server_load.get)
            self.state.chatrooms[room] = target
            self.state.server_load[target] += 1

            for saddr in self.state.servers.values():
                self.send(saddr, {
                    "type": ROOM_ASSIGNMENT_UPDATE,
                    "room": room,
                    "server_id": target
                })

            print(f"[ROOM] Created '{room}' on server {target}")

        owner = self.state.chatrooms[room]
        self.send(addr, {
            "type": ROOM_ASSIGNMENT,
            "room": room,
            "server_addr": self.state.servers[owner]
        })


# ---------------- Main ----------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    server = Server(args.id, args.port)

    if args.id == 1:
        server.state.is_leader = True
        server.state.leader_id = 1
        server.state.leader_addr = server.addr
        print("[LEADER] I am the leader")
    else:
        server.send(("127.0.0.1", 5001), {
            "type": SERVER_UP,
            "server_id": args.id
        })

    server.heartbeat.start()
    server.receive_loop()
