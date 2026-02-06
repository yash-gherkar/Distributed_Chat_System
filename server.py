# server.py
import socket, threading, json, time, argparse
from state import ServerState
from heartbeat import HeartbeatManager
from election import ElectionManager
from protocol import *

BUFFER_SIZE = 4096

class Server:
    def __init__(self, server_id, host, port, all_servers):
        self.host = host
        self.port = port
        self.state = ServerState(server_id)
        self.state.servers = all_servers
        self.state.server_load = {sid: 0 for sid in all_servers.keys()}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))

        self.election_manager = ElectionManager(self)
        self.heartbeat_manager = HeartbeatManager(self)

        threading.Thread(target=self.receive_loop, daemon=True).start()
        self.heartbeat_manager.start()

        # Ring neighbors
        self.sorted_ids = sorted(list(self.state.servers.keys()) + [self.state.server_id])

    def get_ring_neighbor(self):
        idx = self.sorted_ids.index(self.state.server_id)
        neighbor_idx = (idx + 1) % len(self.sorted_ids)
        neighbor_id = self.sorted_ids[neighbor_idx]
        return self.state.servers.get(neighbor_id, (self.host, self.port))

    def send(self, addr, msg):
        self.sock.sendto(json.dumps(msg).encode(), addr)

    def receive_loop(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                t = msg.get("type")
                if t == CLIENT_JOIN:
                    self.handle_client_join(msg, addr)
                elif t == CREATE_CHATROOM:
                    self.handle_create_chatroom(msg, addr)
                elif t == JOIN_CHATROOM:
                    self.handle_join_chatroom(msg, addr)
                elif t == CHAT_MSG:
                    self.handle_chat_msg(msg)
                elif t == HEARTBEAT:
                    self.state.last_heartbeat["leader"] = time.time()
                elif t in (ELECTION, LEADER_ANNOUNCE):
                    self.election_manager.handle_election_message(msg)
            except Exception as e:
                print("[RECEIVE ERROR]", e)

    # ---------------- Client Handlers ----------------
    def handle_client_join(self, msg, addr):
        cid = msg["client_id"]
        self.state.clients[cid] = addr
        self.send(addr, {"type": CHATROOMS_LIST, "rooms": list(self.state.chatrooms.keys())})

    def handle_create_chatroom(self, msg, addr):
        room = msg["room"]
        cid = msg["client_id"]
        # Assign to server with least load
        target_sid = min(self.state.server_load, key=self.state.server_load.get)
        self.state.chatrooms[room] = [cid]
        self.state.room_assignment[room] = target_sid
        self.state.server_load[target_sid] += 1
        self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": self.state.servers[target_sid]})

    def handle_join_chatroom(self, msg, addr):
        room = msg["room"]
        cid = msg["client_id"]
        if room in self.state.chatrooms:
            self.state.chatrooms[room].append(cid)
        else:
            self.state.chatrooms[room] = [cid]
        server_id = self.state.room_assignment.get(room, self.state.server_id)
        self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": self.state.servers[server_id]})

    def handle_chat_msg(self, msg):
        room = msg["room"]
        if room in self.state.chatrooms:
            for cid in self.state.chatrooms[room]:
                if cid != msg["from"]:
                    addr = self.state.clients.get(cid)
                    if addr:
                        self.send(addr, msg)

# ---------------- Main ----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    # Example static server discovery
    all_servers = {
        1: ("127.0.0.1", 5001),
        2: ("127.0.0.1", 5002),
        3: ("127.0.0.1", 5003),
        4: ("127.0.0.1", 5004)
    }

    server = Server(args.id, "127.0.0.1", args.port, all_servers)
    print(f"[SERVER {args.id}] Running on port {args.port}")

    # Start election if no leader
    if not any(s.is_leader for s in [server.state]):
        server.election_manager.start_election()

    while True:
        time.sleep(1)
