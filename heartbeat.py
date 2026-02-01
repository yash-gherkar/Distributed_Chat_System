# heartbeat.py
import threading, time
from protocol import HEARTBEAT

HEARTBEAT_INTERVAL = 2
HEARTBEAT_TIMEOUT = 6

class HeartbeatManager:
    def __init__(self, server):
        self.server = server

    def start(self):
        threading.Thread(target=self._send_loop, daemon=True).start()
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _send_loop(self):
        while True:
            if self.server.state.is_leader:
                for sid, addr in self.server.state.servers.items():
                    self.server.send(addr, {"type": HEARTBEAT, "from": self.server.state.server_id})
            else:
                if self.server.state.leader_addr:
                    self.server.send(self.server.state.leader_addr, {"type": HEARTBEAT, "from": self.server.state.server_id})
            time.sleep(HEARTBEAT_INTERVAL)

    def _monitor_loop(self):
        while True:
            time.sleep(1)
            if self.server.state.is_leader:
                continue
            last = self.server.state.last_heartbeat.get("leader", 0)
            if time.time() - last > HEARTBEAT_TIMEOUT:
                print(f"[HEARTBEAT] Leader timeout → starting election")
                self.server.election_manager.start_election()
