from protocol import LEADER_ANNOUNCE

class ElectionManager:
    def __init__(self, server):
        self.server = server

    def start_election(self):
        print("[ELECTION] Starting election")
        all_ids = list(self.server.state.servers.keys())
        all_ids.append(self.server.state.server_id)
        new_leader = max(set(all_ids))
        self.announce_leader(new_leader)

    def announce_leader(self, leader_id):
        for addr in self.server.state.servers.values():
            self.server.send(addr, {
                "type": LEADER_ANNOUNCE,
                "leader_id": leader_id
            })

        if leader_id == self.server.state.server_id:
            self.server.state.is_leader = True
            self.server.state.leader_id = leader_id
            self.server.state.leader_addr = self.server.addr
            print("[ELECTION] I am the new leader")
