# server/election.py
from protocol import ELECTION, LEADER_ANNOUNCE

class ElectionManager:
    def __init__(self, server):
        self.server = server

    def start_election(self):
        print("[ELECTION] Starting ring election")
        # form a ring of server_ids
        all_ids = list(self.server.state.servers.keys()) + [self.server.state.server_id]
        sorted_ids = sorted(all_ids)
        idx = sorted_ids.index(self.server.state.server_id)
        next_idx = (idx + 1) % len(sorted_ids)
        next_server = sorted_ids[next_idx]
        # send election message to next server
        msg = {
            "type": ELECTION,
            "origin_id": self.server.state.server_id,
            "max_id": self.server.state.server_id
        }
        self.server.send(self.server.state.servers.get(next_server), msg)

    def handle_election(self, msg):
        origin = msg["origin_id"]
        max_id = msg["max_id"]

        if self.server.state.server_id > max_id:
            max_id = self.server.state.server_id

        # determine next server in ring
        sorted_ids = sorted(list(self.server.state.servers.keys()) + [self.server.state.server_id])
        idx = sorted_ids.index(self.server.state.server_id)
        next_idx = (idx + 1) % len(sorted_ids)
