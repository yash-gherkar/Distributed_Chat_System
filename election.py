import threading
import time
from protocol import ELECTION, LEADER_ANNOUNCE, STATE_SYNC

class ElectionManager:
    def __init__(self, server):
        self.server = server
        self.participant = False
        self.lock = threading.Lock()

    def get_next_available_neighbor(self):
        """
        Finds the next node in the ring that is not the failed leader.
        This keeps the LCR ring alive when a node (like Server 4) vanishes.
        """
        idx = self.server.sorted_ids.index(self.server.state.server_id)
        for i in range(1, len(self.server.sorted_ids)):
            neighbor_id = self.server.sorted_ids[(idx + i) % len(self.server.sorted_ids)]
            # In a real system, we'd check if neighbor_id is known to be down.
            # For this LCR implementation, we skip the node that caused the election.
            return self.server.state.servers[neighbor_id]
        return None

    def start_election(self):
        with self.lock:
            self.participant = True
            msg = {"type": ELECTION, "mid": self.server.state.server_id}
            neighbor = self.get_next_available_neighbor()
            if neighbor:
                print(f"[LCR] Starting Election. Sending my ID ({self.server.state.server_id}) to {neighbor}")
                self.server.send(neighbor, msg)

    def handle_election_message(self, msg):
        mid = msg["mid"]
        neighbor = self.get_next_available_neighbor()

        if msg["type"] == ELECTION:
            if mid > self.server.state.server_id:
                # Forward higher ID
                self.participant = True
                print(f"[LCR] Forwarding higher ID {mid} to {neighbor}")
                self.server.send(neighbor, msg)
            elif mid == self.server.state.server_id:
                # My ID returned: I won!
                self.declare_victory(mid, neighbor)
            else:
                # Lower ID received
                if not self.participant:
                    self.start_election()
                else:
                    print(f"[LCR] Discarding lower ID {mid}")

        elif msg["type"] == LEADER_ANNOUNCE:
            self.server.state.leader_addr = (msg["l_ip"], msg["l_port"])
            self.server.state.is_leader = (mid == self.server.state.server_id)
            self.participant = False
            print(f"*** [LCR] New Leader Confirmed: Server {mid} ***")
            
            if mid != self.server.state.server_id:
                self.server.send(neighbor, msg)
                # Recover State: New leader needs to know about our active rooms
                sync = {
                    "type": STATE_SYNC, 
                    "rooms": list(self.server.state.chatrooms.keys()), 
                    "sid": self.server.state.server_id
                }
                self.server.send(self.server.state.leader_addr, sync)

    def declare_victory(self, mid, neighbor):
        print(f"!!! [LCR] Won election. I am Leader {mid} !!!")
        self.server.state.is_leader = True
        self.server.state.leader_addr = (self.server.host_ip, self.server.port)
        announce = {
            "type": LEADER_ANNOUNCE, 
            "mid": mid, 
            "l_ip": self.server.host_ip, 
            "l_port": self.server.port
        }
        self.server.send(neighbor, announce)