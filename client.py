# mock_client.py
import socket
import json
import threading
import uuid
import time
from protocol import *

BUFFER_SIZE = 4096
#SERVER_ADDR = ("127.0.0.1", 5001)  # initial leader server address

class Client:
    def __init__(self, cid):
        self.id = cid
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))
        self.chat_server = None
        self.room = None
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def send(self, msg, addr=None):
        self.sock.sendto(json.dumps(msg).encode(), addr or SERVER_ADDR)

    def listen(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                self.handle(json.loads(data.decode()), addr)
            except Exception as e:
                print(f"[ERROR] {e}")

    def handle(self, msg, addr):
        t = msg["type"]

        if t == CHATROOMS_LIST:
            print(f"[{self.id}] Available rooms: {msg['rooms']}")
            choice = input(f"[{self.id}] Type room to join or new room name to create: ").strip()
            if choice in msg["rooms"]:
                self.send({"type": JOIN_CHATROOM, "client_id": self.id, "room": choice})
            else:
                self.send({"type": CREATE_CHATROOM, "client_id": self.id, "room": choice})

        elif t == ROOM_ASSIGNMENT:
            self.chat_server = tuple(msg["server_addr"])
            self.room = msg["room"]
            print(f"[{self.id}] Joined room '{self.room}' on server {self.chat_server}")

        elif t == CHAT_MSG:
            if msg["room"] == self.room:
                print(f"[{self.id}] {msg['from']}: {msg['body']}")

    def start(self):
        # Announce to server
        server_addr = self.discover_server()
        self.send({"type": CLIENT_JOIN, "client_id": self.id}, server_addr)

        # Start listening thread
        threading.Thread(target=self.listen, daemon=True).start()

        # Wait until room assigned
        while self.room is None:
            time.sleep(0.1)

        # Chat loop
        while True:
            text = input(f"[{self.id}] > ")
            self.send({
                "type": CHAT_MSG,
                "msg_id": str(uuid.uuid4()),
                "from": self.id,
                "room": self.room,
                "body": text
            }, self.chat_server)

    def discover_server(self):
        broadcast_addr = ("255.255.255.255", 5001)
        self.send({"type": DISCOVER_SERVER}, broadcast_addr)

        data, addr = self.sock.recvfrom(BUFFER_SIZE)
        msg = json.loads(data.decode())

        if msg["type"] == SERVER_ADVERTISEMENT:
            print(f"[DISCOVERY] Found server {msg['server_id']} at {msg['addr']}")
            return tuple(msg["addr"])

if __name__ == "__main__":
    cid = input("Client ID: ")
    Cient(cid).start()
