import socket, json, threading, time
from protocol import *

class Client:
    def __init__(self, cid, server_ip, server_port):
        self.id = cid
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.leader_addr = (server_ip, server_port)
        self.chat_server = None
        self.room = None

    def send(self, msg, addr):
        self.sock.sendto(json.dumps(msg).encode(), addr)

    def listen(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg["type"] == CHATROOMS_LIST:
                    print(f"\nRooms: {msg['rooms'] if msg['rooms'] else 'None'}")
                    choice = input("Room name (or 'r' to refresh): ").strip()
                    if choice.lower() != 'r': self.send({"type": JOIN_CHATROOM, "room": choice}, self.leader_addr)
                    else: self.send({"type": CLIENT_JOIN}, self.leader_addr)
                elif msg["type"] == ROOM_ASSIGNMENT:
                    self.room, self.chat_server = msg["room"], tuple(msg["server_addr"])
                    print(f"Connected to {self.room} on {self.chat_server}")
                elif msg["type"] == CHAT_MSG:
                    if msg['from'] != self.id: print(f"\n[{msg['from']}]: {msg['body']}")
            except: pass

    def start(self):
        threading.Thread(target=self.listen, daemon=True).start()
        self.send({"type": CLIENT_JOIN, "client_id": self.id}, self.leader_addr)
        while not self.room: time.sleep(0.5)
        while True:
            body = input(f"[{self.id}] > ")
            if body: self.send({"type": CHAT_MSG, "from": self.id, "room": self.room, "body": body}, self.chat_server)

if __name__ == "__main__":
    name = input("Client ID: ")
    Client(name, "192.168.178.82", 5004).start()