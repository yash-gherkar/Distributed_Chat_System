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

ACK_TIMEOUT = 5            # seconds
RESEND_CHECK_INTERVAL = 1  # seconds


class Server:
    def __init__(self, server_id, port):
        self.state = ServerState(server_id)

        self.addr = ("", port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.addr)

        self.heartbeat = HeartbeatManager(self)
        self.election = ElectionManager(self)

        print(f"[START] Server {server_id} listening on UDP port {port}")

    # -------------------- Networking --------------------

    def send(self, addr, msg):
        data = json.dumps(msg).encode()
        self.sock.sendto(data, addr)

    def receive_loop(self):
        while True:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            msg = json.loads(data.decode())
            self.handle_message(msg, addr)

    # -------------------- Message Dispatch --------------------

    def handle_message(self, msg, addr):
        msg_type = msg["type"]

        if msg_type == CLIENT_JOIN:
            self.handle_client_join(msg, addr)

        elif msg_type == CHAT_MSG:
            self.handle_chat_message(msg)

        elif msg_type == ACK:
            self.handle_ack(msg)

        elif msg_type == HEARTBEAT:
            self.state.last_heartbeat = time.time()

        elif msg_type == LEADER_ANNOUNCE:
            self.handle_leader_announce(msg, addr)

        elif msg_type == LIST_CHATROOMS:
            # Send back the list of current chatrooms
            self.send(addr, {
                "type": CHATROOMS_LIST,
                "rooms": list(self.state.chatrooms.keys())
            })

    # -------------------- Client Join --------------------

    def handle_client_join(self, msg, addr):
        client_id = msg["client_id"]
        room = msg.get("room", "default")

        self.state.clients[client_id] = addr
        # Create room if it doesn't exist
        self.state.chatrooms.setdefault(room, set()).add(client_id)

        self.send(addr, {
            "type": JOIN_ACK,
            "leader": self.state.is_leader
        })

        print(f"[JOIN] Client {client_id} joined room '{room}'")

    # -------------------- Chat + ACK Logic --------------------

    def handle_chat_message(self, msg):
        msg_id = msg["msg_id"]
        sender = msg["from"]
        room = msg["room"]

        recipients = self.state.chatrooms.get(room, set())

        self.state.pending_acks[msg_id] = {
            "sender": sender,
            "room": room,
            "waiting_for": set(recipients),
            "timestamp": time.time(),
            "message": msg
        }

        print(f"[CHAT] {sender} -> room '{room}' (msg {msg_id})")

        for cid in recipients:
            self.send(self.state.clients[cid], msg)

    def handle_ack(self, msg):
        msg_id = msg["msg_id"]
        client_id = msg["from"]

        entry = self.state.pending_acks.get(msg_id)
        if not entry:
            return

        entry["waiting_for"].discard(client_id)

        if not entry["waiting_for"]:
            sender = entry["sender"]
            self.send(self.state.clients[sender], {
                "type": DELIVERED,
                "msg_id": msg_id
            })
            del self.state.pending_acks[msg_id]

            print(f"[DELIVERED] Message {msg_id}")

    # -------------------- Resend Logic --------------------

    def start_resend_monitor(self):
        def monitor():
            while True:
                now = time.time()
                for msg_id, entry in list(self.state.pending_acks.items()):
                    if now - entry["timestamp"] > ACK_TIMEOUT:
                        sender = entry["sender"]

                        print(f"[RESEND] Requesting resend of {msg_id}")

                        self.send(self.state.clients[sender], {
                            "type": RESEND_REQUEST,
                            "msg_id": msg_id
                        })

                        entry["timestamp"] = now

                time.sleep(RESEND_CHECK_INTERVAL)

        threading.Thread(target=monitor, daemon=True).start()

    # -------------------- Election --------------------

    def start_election(self):
        self.election.start_election()

    def handle_leader_announce(self, msg, addr):
        leader_id = msg["leader_id"]

        self.state.is_leader = (leader_id == self.state.server_id)
        self.state.leader_addr = addr

        print(f"[LEADER] New leader elected: Server {leader_id}")


# -------------------- Main --------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    server = Server(args.id, args.port)

    server.heartbeat.start()
    server.start_resend_monitor()
    server.receive_loop()
