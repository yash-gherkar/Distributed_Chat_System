import threading
from protocol import ELECTION, LEADER_ANNOUNCE, STATE_SYNC

class ElectionManager:
    def __init__(self, server):
        self.server = server
        self.participant = False
        self.lock = threading.Lock()

    def start_election(self):
        with self.lock:
            self.participant = True
            msg = {"type": ELECTION, "mid": self.server.state.server_id}
            neighbor = self.server.get_ring_neighbor()
            self.server.send(neighbor, msg)

    def handle_election_message(self, msg):
        mid = msg["mid"]
        neighbor = self.server.get_ring_neighbor()

        if msg["type"] == ELECTION:
            if mid > self.server.state.server_id:
                self.participant = True
                self.server.send(neighbor, msg)
            elif mid == self.server.state.server_id:
                print(f"[LCR] Won election. Announcing ID {mid}...")
                self.server.state.is_leader = True
                self.server.state.leader_addr = (self.server.host_ip, self.server.port)
                announce = {"type": LEADER_ANNOUNCE, "mid": mid, "l_ip": self.server.host_ip, "l_port": self.server.port}
                self.server.send(neighbor, announce)
            else:
                if not self.participant: self.start_election()

        elif msg["type"] == LEADER_ANNOUNCE:
            self.server.state.leader_addr = (msg["l_ip"], msg["l_port"])
            self.server.state.is_leader = (mid == self.server.state.server_id)
            self.participant = False
            print(f"[LCR] New Leader: Server {mid}")
            if mid != self.server.state.server_id:
                self.server.send(neighbor, msg)
                # Sync local rooms to new leader for recovery
                sync = {"type": STATE_SYNC, "rooms": list(self.server.state.chatrooms.keys()), "sid": self.server.state.server_id}
                self.server.send(self.server.state.leader_addr, sync)