# client.py
import socket, json, threading, time, uuid
from protocol import *

BUFFER_SIZE = 4096

class Client:
    def __init__(self, cid, server_addr):
        self.id = cid
        self.server_addr = server_addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))
        self.room = None

    def send(self, msg, addr=None):
        self.sock.sendto(json.dumps(msg).encode(), addr or self.server_addr)

    def listen(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                t = msg.get("type")
                if t == CHATROOMS_LIST:
                    print(f"[{self.id}] Rooms: {msg['rooms']}")
                    choice = input("Room to join or create: ").strip()
                    if choice in msg["rooms"]:
                        self.send({"type": JOIN_CHATROOM, "client_id": self.id, "room": choice})
                    else:
                        self.send({"type": CREATE_CHATROOM, "client_id": self.id, "room": choice})
                elif t == ROOM_ASSIGNMENT:
                    self.room = msg["room"]
                    print(f"[{self.id}] Joined {self.room} at server {msg['server_addr']}")
                elif t == CHAT_MSG and msg.get("room") == self.room:
                    print(f"{msg['from']}: {msg['body']}")
            except Exception as e:
                print(f"[CLIENT ERROR] {e}")

    def start(self):
        self.send({"type": CLIENT_JOIN, "client_id": self.id})
        threading.Thread(target=self.listen, daemon=True).start()
        while self.room is None:
            time.sleep(0.1)
        while True:
            text = input(f"[{self.id}] > ")
            self.send({"type": CHAT_MSG, "from": self.id, "room": self.room, "body": text, "msg_id": str(uuid.uuid4())})

if __name__ == "__main__":
    cid = input("Client ID: ")
    client = Client(cid, ("127.0.0.1", 5001))
    client.start()
