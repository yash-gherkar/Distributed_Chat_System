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
                for addr in self.server.state.servers.values():
                    self.server.send(addr, {
                        "type": HEARTBEAT,
                        "leader_id": self.server.state.server_id
                    })
            time.sleep(HEARTBEAT_INTERVAL)

    def _monitor_loop(self):
        while True:
            if not self.server.state.is_leader:
                if time.time() - self.server.state.last_heartbeat > HEARTBEAT_TIMEOUT:
                    print("[HEARTBEAT] Leader timeout detected")
                    self.server.election.start_election()
                    time.sleep(HEARTBEAT_TIMEOUT)
            time.sleep(1)
