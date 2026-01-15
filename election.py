# election.py
import threading
import time
import pickle
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
            # Ring election message: {'mid': unique_id, 'IP': sender IP, 'isLeader': False}
            msg = {
                "mid": self.server.state.server_id,
                "IP": self.server.addr[0],
                "isLeader": False
            }
            neighbor = self.server.get_ring_neighbor()
            self.server.send(neighbor, msg)

    def handle_election_message(self, msg):
        """Handle incoming election message"""
        msg_mid = msg["mid"]
        msg_ip = msg["IP"]
        is_leader = msg["isLeader"]

        if is_leader:
            # Leader announcement
            self.server.state.leader_addr = (msg_ip, self.server.server_port)
            self.server.state.is_leader = (msg_ip == self.server.addr[0])
            print(f"[ELECTION] Leader announced: {msg_ip}")
            self.participant = False
            return

        if msg_mid > self.server.state.server_id:
            # Forward the message
            neighbor = self.server.get_ring_neighbor()
            self.server.send(neighbor, msg)
            self.participant = True
        elif msg_mid < self.server.state.server_id and not self.participant:
            # Replace and forward
            new_msg = {
                "mid": self.server.state.server_id,
                "IP": self.server.addr[0],
                "isLeader": False
            }
            neighbor = self.server.get_ring_neighbor()
            self.server.send(neighbor, new_msg)
            self.participant = True
        elif msg_mid == self.server.state.server_id:
            # I am the leader now
            announce = {
                "mid": self.server.state.server_id,
                "IP": self.server.addr[0],
                "isLeader": True
            }
            neighbor = self.server.get_ring_neighbor()
            self.server.send(neighbor, announce)
            self.server.state.is_leader = True
            self.server.state.leader_addr = self.server.addr
            print(f"[ELECTION] I am the new leader")
            self.participant = False
