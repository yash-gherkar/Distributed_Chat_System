# election.py
import threading
import time
from protocol import ELECTION, LEADER_ANNOUNCE

class ElectionManager:
    def __init__(self, server):
        self.server = server
        self.lock = threading.Lock()
        self.waiting_for_responses = False

    def start_election(self):
        with self.lock:
            print(f"[ELECTION] Server {self.server.state.server_id} starting Bully election")
            # Find all servers with an ID higher than mine
            higher_servers = {sid: addr for sid, addr in self.server.state.servers.items() 
                              if sid > self.server.state.server_id}

            if not higher_servers:
                # I am the highest ID; I win immediately
                self.announce_victory()
            else:
                self.waiting_for_responses = True
                for sid, addr in higher_servers.items():
                    self.server.send(addr, {"type": ELECTION, "mid": self.server.state.server_id})
                
                # Wait to see if a higher ID responds
                threading.Thread(target=self._wait_for_answers, daemon=True).start()

    def _wait_for_answers(self):
        time.sleep(2.0) # 2s window for higher nodes to "Bully" back
        with self.lock:
            if self.waiting_for_responses:
                self.announce_victory()

    def handle_election_message(self, msg):
        m_type = msg.get("type")
        mid = msg.get("mid")

        if m_type == ELECTION:
            if mid < self.server.state.server_id:
                # A lower ID challenged; I am higher, so I take over
                self.start_election()
        elif m_type == LEADER_ANNOUNCE:
            with self.lock:
                self.waiting_for_responses = False
                self.server.state.is_leader = (mid == self.server.state.server_id)
                self.server.state.leader_addr = self.server.state.servers.get(mid)
                print(f"[ELECTION] New Leader: {mid}")

    def announce_victory(self):
        self.waiting_for_responses = False
        self.server.state.is_leader = True
        self.server.state.leader_addr = (self.server.host, self.server.port)

        # ADD THIS LINE TO SEE THE CONFIRMATION
        print(f"[ELECTION] I am the new leader (Server {self.server.state.server_id})")

        msg = {"type": LEADER_ANNOUNCE, "mid": self.server.state.server_id}
        for sid, addr in self.server.state.servers.items():
            if sid != self.server.state.server_id:
                self.server.send(addr, msg)