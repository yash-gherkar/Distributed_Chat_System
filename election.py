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
            print(f"[ELECTION] Server {self.server.id} starting ring election")
            msg = {"mid": self.server.id, "isLeader": False}
            neighbor = self.server.get_ring_neighbor()
            if neighbor:
                self.server.send(neighbor, {"type": ELECTION, **msg})

    def handle_election_message(self, msg):
        mid = msg["mid"]
        is_leader = msg["isLeader"]
        neighbor = self.server.get_ring_neighbor()

        if is_leader:
            # Leader announced
            self.server.state.leader_addr = neighbor
            self.server.state.is_leader = (mid == self.server.id)
            print(f"[ELECTION] Leader announced: {mid}")
            self.participant = False
            return

        # Forward or replace
        if mid > self.server.id:
            # Forward
            if neighbor:
                self.server.send(neighbor, msg)
            self.participant = True
        elif mid < self.server.id and not self.participant:
            # Replace and forward
            new_msg = {"mid": self.server.id, "isLeader": False}
            if neighbor:
                self.server.send(neighbor, new_msg)
            self.participant = True
        elif mid == self.server.id:
            # I am leader
            announce = {"mid": self.server.id, "isLeader": True}
            if neighbor:
                self.server.send(neighbor, announce)
            self.server.state.is_leader = True
            self.server.state.leader_addr = (self.server.host, self.server.port)
            print(f"[ELECTION] I am the new leader")
            self.participant = False
