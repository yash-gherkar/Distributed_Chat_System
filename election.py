import threading
from protocol import ELECTION, LEADER_ANNOUNCE

class ElectionManager:
    def __init__(self, server):
        self.server = server
        self.participant = False
        self.lock = threading.Lock()

    def start_election(self):
        with self.lock:
            print("[ELECTION] Starting ring election")
            self.participant = True
            msg = {"mid": self.server.state.server_id, "IP": "127.0.0.1", "isLeader": False}
            neighbor = self.get_ring_neighbor()
            self.server.send(neighbor, {"type": "ELECTION_MSG", **msg})

    def handle_election_message(self, msg):
        mid = msg["mid"]
        is_leader = msg["isLeader"]
        if is_leader:
            self.server.state.leader_addr = (msg["IP"], self.server.state.port)
            self.server.state.is_leader = (msg["IP"] == "127.0.0.1")
            print(f"[ELECTION] Leader announced: {self.server.state.leader_addr}")
            self.participant = False
            return

        if mid > self.server.state.server_id:
            neighbor = self.get_ring_neighbor()
            self.server.send(neighbor, msg)
            self.participant = True
        elif mid < self.server.state.server_id and not self.participant:
            new_msg = {"mid": self.server.state.server_id, "IP": "127.0.0.1", "isLeader": False}
            neighbor = self.get_ring_neighbor()
            self.server.send(neighbor, new_msg)
            self.participant = True
        elif mid == self.server.state.server_id:
            announce = {"mid": self.server.state.server_id, "IP": "127.0.0.1", "isLeader": True}
            neighbor = self.get_ring_neighbor()
            self.server.send(neighbor, announce)
            self.server.state.is_leader = True
            self.server.state.leader_addr = ("127.0.0.1", self.server.state.port)
            print("[ELECTION] I am the new leader")
            self.participant = False

    def get_ring_neighbor(self):
        """Return next server in ring based on ID"""
        ids = sorted(list(self.server.state.servers.keys()) + [self.server.state.server_id])
        idx = ids.index(self.server.state.server_id)
        next_idx = (idx + 1) % len(ids)
        next_id = ids[next_idx]
        if next_id == self.server.state.server_id:
            return ("127.0.0.1", self.server.state.port)
        return self.server.state.servers[next_id]
