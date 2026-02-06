# server.py
import socket, threading, json, time, argparse
from state import ServerState
from heartbeat import HeartbeatManager
from election import ElectionManager
from protocol import *

BUFFER_SIZE = 4096
BROADCAST_PORT = 5005  # Dedicated port for discovery pings

class Server:
    def __init__(self, server_id, host, port):
        self.host = host
        self.port = port
        self.state = ServerState(server_id)
        
        # Start with an empty server map
        self.state.servers = {} 
        self.state.server_load = {}
        
        # Main communication socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((host, port))

        # Discovery socket (Listens specifically for broadcasts)
        self.discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Allow multiple servers to bind to the same broadcast port on one machine
        self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            
        self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_sock.bind(('', BROADCAST_PORT))

        self.election_manager = ElectionManager(self)
        self.heartbeat_manager = HeartbeatManager(self)

        # Start all responsibility threads
        threading.Thread(target=self.receive_loop, daemon=True).start()
        threading.Thread(target=self.discovery_listener, daemon=True).start()
        self.heartbeat_manager.start()

        # Announce presence to the network
        self.broadcast_presence()

    def broadcast_presence(self):
        """Sends a 'shout' to find other servers."""
        msg = {
            "type": DISCOVERY_PING,
            "server_id": self.state.server_id,
            "addr": (self.host, self.port)
        }
        print(f"[DISCOVERY] Broadcasting presence...")
        # Use <broadcast> to reach everyone on the local subnet
        self.sock.sendto(json.dumps(msg).encode(), ('<broadcast>', BROADCAST_PORT))

    def discovery_listener(self):
        """Hears other servers or clients joining the cluster."""
        while True:
            try:
                data, addr = self.discovery_sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                
                if msg.get("type") == DISCOVERY_PING:
                    sid = msg["server_id"]
                    
                    # IF IT'S A CLIENT: Just reply so they can connect
                    if sid == "CLIENT":
                        print(f"[DISCOVERY] Client seeking server from {addr}")
                        reply = {
                            "type": DISCOVERY_PONG, 
                            "server_id": self.state.server_id, 
                            "addr": (self.host, self.port)
                        }
                        self.send(addr, reply) # Use 'addr' from recvfrom, not msg['addr']
                    
                    # IF IT'S A SERVER: Add to map and start election
                    elif sid != self.state.server_id and sid not in self.state.servers:
                        s_addr = tuple(msg["addr"])
                        print(f"[DISCOVERY] Found Server {sid} at {s_addr}")
                        self.state.servers[sid] = s_addr
                        self.state.server_load[sid] = 0
                        
                        reply = {
                            "type": DISCOVERY_PONG, 
                            "server_id": self.state.server_id, 
                            "addr": (self.host, self.port)
                        }
                        self.send(s_addr, reply)
                        self.election_manager.start_election()
            except Exception as e:
                print(f"[DISCOVERY ERROR] {e}")

    def send(self, addr, msg):
        try:
            self.sock.sendto(json.dumps(msg).encode(), addr)
        except Exception as e:
            print(f"[SEND ERROR] to {addr}: {e}")

    def receive_loop(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode())
                t = msg.get("type")

                # New Discovery Response Handler
                if t == DISCOVERY_PONG:
                    sid = msg["server_id"]
                    s_addr = tuple(msg["addr"])
                    if sid not in self.state.servers:
                        print(f"[DISCOVERY] Learned about Server {sid} at {s_addr}")
                        self.state.servers[sid] = s_addr
                        self.state.server_load[sid] = 0
                        self.election_manager.start_election()

                # --- Your Original Handlers ---
                elif t == CLIENT_JOIN:
                    self.handle_client_join(msg, addr)
                elif t == CREATE_CHATROOM:
                    self.handle_create_chatroom(msg, addr)
                elif t == JOIN_CHATROOM:
                    self.handle_join_chatroom(msg, addr)
                elif t == CHAT_MSG:
                    self.handle_chat_msg(msg)
                elif t == CLIENT_REGISTER:
                    self.handle_client_register(msg)
                elif t == HEARTBEAT:
                    self.state.last_heartbeat["leader"] = time.time()
                elif t in (ELECTION, BULLY_OK, LEADER_ANNOUNCE):
                    self.election_manager.handle_election_message(msg)
                    
            except Exception as e:
                print(f"[RECEIVE ERROR] {e}")

    # ---------------- Your Original Handlers ----------------

    def handle_client_join(self, msg, addr):
        cid = msg["client_id"]
        self.state.clients[cid] = addr
        print(f"[SERVER {self.state.server_id}] Local Client {cid} joined.")

        if not self.state.is_leader and self.state.leader_addr:
            notice = {
                "type": CLIENT_REGISTER, 
                "client_id": cid, 
                "client_addr": addr, 
                "on_server": self.state.server_id
            }
            self.send(self.state.leader_addr, notice)
        
        self.send(addr, {"type": CHATROOMS_LIST, "rooms": list(self.state.chatrooms.keys())})

    def handle_client_register(self, msg):
        if not self.state.is_leader: return
        cid = msg["client_id"]
        c_addr = tuple(msg["client_addr"]) 
        self.state.clients[cid] = c_addr
        print(f"[LEADER] Registered remote client {cid} from Server {msg['on_server']}")

    def handle_create_chatroom(self, msg, addr):
        room = msg["room"]
        cid = msg["client_id"]
        target_sid = min(self.state.server_load, key=self.state.server_load.get)
        self.state.chatrooms[room] = [cid]
        self.state.room_assignment[room] = target_sid
        self.state.server_load[target_sid] += 1
        self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": self.state.servers[target_sid]})

    def handle_join_chatroom(self, msg, addr):
        room = msg["room"]
        cid = msg["client_id"]
        if room not in self.state.chatrooms:
            self.state.chatrooms[room] = []
        self.state.chatrooms[room].append(cid)
        server_id = self.state.room_assignment.get(room, self.state.server_id)
        self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": self.state.servers[server_id]})

    def handle_chat_msg(self, msg):
        room = msg["room"]
        sender = msg["from"]
        encrypted_body = msg["body"] # The body is already encrypted by the client
        
        if room in self.state.chatrooms:
            for cid in self.state.chatrooms[room]:
                if cid != sender:
                    # Log the encrypted message as requested
                    print(f"[CHAT] {sender} has sent '{encrypted_body}' to {cid}")
                    
                    addr = self.state.clients.get(cid)
                    if addr:
                        self.send(addr, msg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    # CHANGE "127.0.0.1" TO "" HERE
    server = Server(args.id, "", args.port) 
    print(f"[SERVER {args.id}] Running with Dynamic Discovery on port {args.port}")

    while True:
        time.sleep(1)