import socket, threading, json, time, argparse
from state import ServerState
from heartbeat import HeartbeatManager
from election import ElectionManager
from protocol import *

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except: ip = '127.0.0.1'
    finally: s.close()
    return ip

class Server:
    def __init__(self, server_id, port, all_servers):
        self.port = port
        self.host_ip = get_my_ip()
        self.state = ServerState(server_id)
        self.state.servers = all_servers
        self.state.server_load = {sid: 0 for sid in all_servers.keys()}
        self.sorted_ids = sorted(list(all_servers.keys()))
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", port))
        
        self.election_manager = ElectionManager(self)
        self.heartbeat_manager = HeartbeatManager(self)
        self.state.last_heartbeat["leader"] = time.time()
        
        threading.Thread(target=self.receive_loop, daemon=True).start()
        self.heartbeat_manager.start()

    def get_ring_neighbor(self):
        idx = self.sorted_ids.index(self.state.server_id)
        return self.state.servers[self.sorted_ids[(idx + 1) % len(self.sorted_ids)]]

    def send(self, addr, msg):
        try: self.sock.sendto(json.dumps(msg).encode(), tuple(addr))
        except: pass

    def receive_loop(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                msg = json.loads(data.decode())
                t = msg.get("type")
                
                if t == HEARTBEAT:
                    self.state.last_heartbeat["leader"] = time.time()
                elif t in (ELECTION, LEADER_ANNOUNCE):
                    self.election_manager.handle_election_message(msg)
                elif t == STATE_SYNC and self.state.is_leader:
                    for r in msg.get("rooms", []):
                        if r not in self.state.room_assignment:
                            self.state.room_assignment[r] = msg["sid"]
                            self.state.server_load[msg["sid"]] += 1
                elif t == CLIENT_JOIN:
                    rooms = list(self.state.room_assignment.keys())
                    self.send(addr, {"type": CHATROOMS_LIST, "rooms": rooms})
                elif t in (CREATE_CHATROOM, JOIN_CHATROOM):
                    room = msg["room"]
                    if self.state.is_leader:
                        if room not in self.state.room_assignment:
                            target_sid = min(self.state.server_load, key=self.state.server_load.get)
                            self.state.room_assignment[room] = target_sid
                            self.state.server_load[target_sid] += 1
                        assigned_sid = self.state.room_assignment[room]
                        self.send(addr, {"type": ROOM_ASSIGNMENT, "room": room, "server_addr": self.state.servers[assigned_sid]})
                    else:
                        if self.state.leader_addr: self.send(self.state.leader_addr, msg)
                elif t == CHAT_MSG:
                    room, sender = msg["room"], msg["from"]
                    if room not in self.state.chatrooms: self.state.chatrooms[room] = []
                    if sender not in self.state.chatrooms[room]: self.state.chatrooms[room].append(sender)
                    self.state.clients[sender] = addr
                    print(f"[{room}] {sender}: {msg['body']}")
                    for cid in self.state.chatrooms[room]:
                        if cid != sender:
                            target = self.state.clients.get(cid)
                            if target: self.send(target, msg)
            except: pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    MY_IP = get_my_ip()
    config = {1: (MY_IP, 5001), 3: (MY_IP, 5003), 4: (MY_IP, 5004)}
    print(f"--- SERVER {args.id} STARTING ---")
    Server(args.id, args.port, config)
    while True: time.sleep(1)