# election.py
import threading
from protocol import ELECTION, LEADER_ANNOUNCE

class ElectionManager:
    def __init__(self, server):
        self.server = server
        self.participant = False
        self.lock = threading.Lock()

    def start_election(self):
        with self.lock:
            if self.participant:
                return
            self.participant = True
            print(f"[ELECTION] Server {self.server.state.server_id} starting ring election")
            msg = {"type": ELECTION, "mid": self.server.state.server_id, "isLeader": False}
            neighbor = self.server.get_ring_neighbor()
            if neighbor:
                self.server.send(neighbor, msg)

    def handle_election_message(self, msg):
        mid = msg["mid"]
        is_leader = msg["isLeader"]
        neighbor = self.server.get_ring_neighbor()

        if is_leader:
            # Leader announcement
            self.server.state.leader_addr = (neighbor[0], neighbor[1])
            self.server.state.is_leader = (mid == self.server.state.server_id)
            print(f"[ELECTION] Leader announced: {mid}")
            self.participant = False
            return

        # Chang–Roberts logic
        if mid > self.server.state.server_id:
            if neighbor:
                self.server.send(neighbor, msg)
            self.participant = True
        elif mid < self.server.state.server_id and not self.participant:
            new_msg = {"type": ELECTION, "mid": self.server.state.server_id, "isLeader": False}
            if neighbor:
                self.server.send(neighbor, new_msg)
            self.participant = True
        elif mid == self.server.state.server_id:
            # I am the new leader
            announce = {"type": LEADER_ANNOUNCE, "mid": self.server.state.server_id, "isLeader": True}
            if neighbor:
                self.server.send(neighbor, announce)
            self.server.state.is_leader = True
            self.server.state.leader_addr = (self.server.host, self.server.port)
            print(f"[ELECTION] I am the new leader")
            self.participant = False
