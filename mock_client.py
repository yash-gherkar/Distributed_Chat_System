import socket
import json
import threading
import uuid

SERVER_ADDR = ("127.0.0.1", 5001)
BUFFER_SIZE = 4096


class MockClient:
    def __init__(self, cid):
        self.id = cid
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))
        self.chat_server = None
        self.room = None

    def send(self, msg, addr=None):
        self.sock.sendto(json.dumps(msg).encode(), addr or SERVER_ADDR)

    def listen(self):
        while True:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            self.handle(json.loads(data.decode()), addr)

    def handle(self, msg, addr):
        t = msg["type"]

        if t == CHATROOMS_LIST:
            print("Available rooms:", msg["rooms"])

        elif t == ROOM_ASSIGNMENT:
            self.chat_server = tuple(msg["server_addr"])
            self.room = msg["room"]
            print(f"[JOINED] {self.room} on {self.chat_server}")

        elif t == CHAT_MSG:
            print(f"{msg['from']}: {msg['body']}")

    def start(self):
        self.send({"type": CLIENT_JOIN, "client_id": self.id})

        room = input("Enter chatroom name: ")
        self.send({"type": CREATE_CHATROOM, "room": room})

        threading.Thread(target=self.listen, daemon=True).start()

        while True:
            text = input("> ")
            self.send({
                "type": CHAT_MSG,
                "msg_id": str(uuid.uuid4()),
                "from": self.id,
                "room": self.room,
                "body": text
            }, self.chat_server)


if __name__ == "__main__":
    cid = input("Client ID: ")
    MockClient(cid).start()