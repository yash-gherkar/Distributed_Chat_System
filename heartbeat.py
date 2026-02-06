import threading, time
from protocol import HEARTBEAT

class HeartbeatManager:
    def __init__(self, server):
        self.server = server
        self.interval = 2
        self.timeout = 6

    def start(self):
        threading.Thread(target=self._send_loop, daemon=True).start()
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _send_loop(self):
        while True:
            if self.server.state.is_leader:
                for sid, addr in self.server.state.servers.items():
                    if sid != self.server.state.server_id:
                        self.server.send(addr, {"type": HEARTBEAT})
            time.sleep(self.interval)

    def _monitor_loop(self):
        time.sleep(self.timeout) 
        while True:
            time.sleep(1)
            if not self.server.state.is_leader:
                last_time = self.server.state.last_heartbeat.get("leader", 0)
                elapsed = time.time() - last_time
                
                if elapsed > self.timeout and not self.server.election_manager.participant:
                    print(f"[FAULT] Leader timeout ({elapsed:.1f}s). Starting LCR Election...")
                    self.server.election_manager.start_election()
                    self.server.state.last_heartbeat["leader"] = time.time()