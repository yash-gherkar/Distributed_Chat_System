import socket
import json
import threading
import uuid
import time
from protocol import *

BUFFER_SIZE = 4096
DISCOVERY_PORT = 5000  # must match server

class Client:
    def __init__(self, cid):
        self.id = cid
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.chat_server = None
        self.room = None

    def send(self, msg, addr):
        self.sock.sendto(json.dumps(msg).encode(), addr)

    def listen(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                self.handle(json.loads(data.decode()), addr)
            except:
                pass

    def handle(self, msg, addr):
        t = msg["type"]
        if t == CHATROOMS_LIST:
            print(f"[{self.id}] Available rooms: {msg['rooms']}")
            choice = input(f"[{self.id}] Type room to join or new room name to create: ").strip()
            if choice in msg["rooms"]:
                self.send({"type": JOIN_CHATROOM, "client_id": self.id, "room": choice}, self.chat_server)
            else:
                self.send({"type": CREATE_CHATROOM, "client_id": self.id, "room": choice}, self.chat_server)

        elif t == ROOM_ASSIGNMENT:
            self.chat_server = tuple(msg["server_addr"])
            self.room = msg["room"]
            print(f"[{self.id}] Joined room '{self.room}' on server {self.chat_server}")

        elif t == CHAT_MSG:
            if msg["room"] == self.room:
                print(f"[{self.id}] {msg['from']}: {msg['body']}")

    # -------------------- Discovery --------------------
    def discover_server(self, timeout=5):
        broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_sock.settimeout(timeout)
        msg = {"type": DISCOVER_SERVER}
        broadcast_sock.sendto(json.dumps(msg).encode(), ('<broadcast>', DISCOVERY_PORT))
        try:
            data, addr = broadcast_sock.recvfrom(BUFFER_SIZE)
            reply = json.loads(data.decode())
            if reply["type"] == SERVER_ADVERTISEMENT:
                print(f"[DISCOVERY] Found server {reply['server_id']} at {reply['addr']}")
                return tuple(reply['addr'])
        except:
            print("[DISCOVERY] No servers found, retrying...")
            time.sleep(1)
            return self.discover_server()

    def start(self):
        self.chat_server = self.discover_server()
        # Announce to server
        self.send({"type": CLIENT_JOIN, "client_id": self.id}, self.chat_server)

        threading.Thread(target=self.listen, daemon=True).start()
        while self.room is None:
            time.sleep(0.1)

        while True:
            text = input(f"[{self.id}] > ")
            self.send({
                "type": CHAT_MSG,
                "msg_id": str(uuid.uuid4()),
                "from": self.id,
                "room": self.room,
                "body": text
            }, self.chat_server)

if __name__ == "__main__":
    cid = input("Client ID: ")
    Client(cid).start()
