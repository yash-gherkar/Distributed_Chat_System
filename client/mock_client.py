import socket
import json
import uuid
import threading
import time

SERVER_ADDR = ("127.0.0.1", 5001)
BUFFER_SIZE = 4096


class MockClient:
    def __init__(self, client_id):
        self.client_id = client_id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))  # random port

        self.pending_messages = {}  # msg_id -> message

    def send(self, msg):
        self.sock.sendto(json.dumps(msg).encode(), SERVER_ADDR)

    def join(self, room="default"):
        self.send({
            "type": "CLIENT_JOIN",
            "client_id": self.client_id,
            "room": room
        })

    def send_message(self, room, text):
        msg_id = str(uuid.uuid4())
        msg = {
            "type": "CHAT_MSG",
            "msg_id": msg_id,
            "from": self.client_id,
            "room": room,
            "body": text
        }

        self.pending_messages[msg_id] = msg
        self.send(msg)

    def listen(self):
        while True:
            data, _ = self.sock.recvfrom(BUFFER_SIZE)
            msg = json.loads(data.decode())
            self.handle(msg)

    def handle(self, msg):
        t = msg["type"]

        if t == "CHAT_MSG":
            print(f"[RECV] {msg['from']}: {msg['body']}")

            # send ACK
            self.send({
                "type": "ACK",
                "msg_id": msg["msg_id"],
                "from": self.client_id
            })

        elif t == "DELIVERED":
            print(f"[DELIVERED] Message {msg['msg_id']}")
            self.pending_messages.pop(msg["msg_id"], None)

        elif t == "RESEND_REQUEST":
            msg_id = msg["msg_id"]
            print(f"[RESEND_REQUEST] {msg_id}")
            if msg_id in self.pending_messages:
                self.send(self.pending_messages[msg_id])


if __name__ == "__main__":
    cid = input("Client ID: ")
    client = MockClient(cid)
    client.join()

    threading.Thread(target=client.listen, daemon=True).start()

    while True:
        text = input("> ")
        client.send_message("default", text)
