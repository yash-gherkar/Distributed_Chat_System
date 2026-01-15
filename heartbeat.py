# heartbeat.py
import threading
import time
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
            now = time.time()
            if not self.server.state.is_leader:
                last = self.server.state.last_heartbeat.get("leader", 0)
                if now - last > HEARTBEAT_TIMEOUT:
                    print("[HEARTBEAT] Leader timeout detected")
                    self.server.election_manager.start_election()
            time.sleep(1)
