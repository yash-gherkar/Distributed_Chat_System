# client.py
import socket, json, threading, time
from protocol import *
from cipher import encrypt, decrypt

BUFFER_SIZE = 4096
BROADCAST_PORT = 5005

class Client:
    def __init__(self, cid):
        self.id = cid
        self.server_addr = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.room = None

    def find_server(self):
        """Broadcasts to find a server entry point."""
        print("Searching for available servers...")
        msg = {"type": DISCOVERY_PING, "server_id": "CLIENT", "addr": ("", 0)}
        
        # Try a specific broadcast address for better macOS compatibility
        self.sock.sendto(json.dumps(msg).encode(), ('255.255.255.255', BROADCAST_PORT))
        
        self.sock.settimeout(3.0)
        try:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            msg = json.loads(data.decode())
            if msg["type"] == DISCOVERY_PONG:
                self.server_addr = tuple(msg["addr"])
                # Use the actual IP from the sender if the message says 127.0.0.1
                if self.server_addr[0] == "127.0.0.1" or self.server_addr[0] == "":
                    self.server_addr = (addr[0], self.server_addr[1])
                print(f"Connected to Server at {self.server_addr}")
        except socket.timeout:
            print("No servers found. Retrying...")
            self.find_server() # Recursive retry
        self.sock.settimeout(None)

    def send(self, msg):
        self.sock.sendto(json.dumps(msg).encode(), self.server_addr)

    def listen(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                t = msg.get("type")
                if t == CHATROOMS_LIST:
                    print(f"\n--- Available Rooms: {msg['rooms']} ---")
                    choice = input("Join or Create: ").strip()
                    self.send({"type": JOIN_CHATROOM if choice in msg["rooms"] else CREATE_CHATROOM, "client_id": self.id, "room": choice})
                elif t == ROOM_ASSIGNMENT:
                    self.room = msg["room"]
                    print(f"\n>>> Joined: {self.room} via {msg['server_addr']}\n")
                elif t == CHAT_MSG and msg.get("room") == self.room:
                    # Decrypt the body before printing for the user
                    original_body = decrypt(msg['body'])
                    print(f"\r{msg['from']}: {original_body}")
                    print(f"{self.id} > ", end="", flush=True)
            except Exception: break

    def start(self):
        self.find_server()
        self.send({"type": CLIENT_JOIN, "client_id": self.id})
        threading.Thread(target=self.listen, daemon=True).start()
        while self.room is None: time.sleep(0.1)
        while True:
            text = input(f"{self.id} > ")
            if text.strip():
                # Encrypt the body before putting it into the packet
                encrypted_text = encrypt(text)
                self.send({"type": CHAT_MSG, "from": self.id, "room": self.room, "body": encrypted_text})

if __name__ == "__main__":
    cid = input("Enter Client ID: ").strip()
    client = Client(cid)
    client.start()