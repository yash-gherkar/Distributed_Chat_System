# server.py
import argparse
import threading
import time
import json

from protocol import *
from state import *

class Server:
    def __init__(self, server_id, ip):
        self.id = server_id
        self.ip = ip

        self.leader_id = None
        self.leader_ip = None
        self.is_leader = False

        self.servers = {}  # id -> ip
        self.last_heartbeat = time.time()

    # ---------------- DISCOVERY ----------------
    def discovery_listener(self):
        sock = udp_socket("", BROADCAST_PORT, broadcast=True)
        while True:
            data, addr = sock.recvfrom(1024)
            msg = json.loads(data.decode())
            if msg["type"] == DISCOVER:
                reply = {
                    "type": DISCOVER_REPLY,
                    "id": self.id,
                    "ip": self.ip
                }
                sock.sendto(json.dumps(reply).encode(), addr)

    def discover_servers(self):
        sock = udp_socket(broadcast=True, timeout=2)
        msg = {"type": DISCOVER, "id": self.id}
        sock.sendto(json.dumps(msg).encode(), ("255.255.255.255", BROADCAST_PORT))
        try:
            while True:
                data, _ = sock.recvfrom(1024)
                reply = json.loads(data.decode())
                self.servers[reply["id"]] = reply["ip"]
        except:
            pass
        sock.close()

    # ---------------- BULLY ELECTION ----------------
    def start_election(self):
        print(f"[SERVER {self.id}] Starting election")
        higher = [sid for sid in self.servers if sid > self.id]

        sock = udp_socket()
        got_ok = False

        for sid in higher:
            try:
                sock.sendto(
                    json.dumps({"type": ELECTION, "from": self.id}).encode(),
                    (self.servers[sid], ELECTION_PORT_BASE + sid)
                )
                got_ok = True
            except:
                pass

        if not got_ok:
            self.become_leader()

    def election_listener(self):
        sock = udp_socket("", ELECTION_PORT_BASE + self.id)
        while True:
            data, addr = sock.recvfrom(1024)
            msg = json.loads(data.decode())

            if msg["type"] == ELECTION:
                sock.sendto(
                    json.dumps({"type": OK}).encode(),
                    addr
                )
                self.start_election()

            elif msg["type"] == COORDINATOR:
                self.leader_id = msg["id"]
                self.leader_ip = msg["ip"]
                self.is_leader = False
                print(f"[SERVER {self.id}] New leader is {self.leader_id}")

    def become_leader(self):
        self.is_leader = True
        self.leader_id = self.id
        self.leader_ip = self.ip
        print(f"[SERVER {self.id}] I AM THE LEADER")

        sock = udp_socket()
        for sid, ip in self.servers.items():
            sock.sendto(
                json.dumps({
                    "type": COORDINATOR,
                    "id": self.id,
                    "ip": self.ip
                }).encode(),
                (ip, ELECTION_PORT_BASE + sid)
            )

    # ---------------- HEARTBEAT ----------------
    def heartbeat_sender(self):
        sock = udp_socket()
        while True:
            if self.is_leader:
                for sid, ip in self.servers.items():
                    sock.sendto(
                        json.dumps({"type": HEARTBEAT}).encode(),
                        (ip, HEARTBEAT_PORT_BASE + sid)
                    )
            time.sleep(HEARTBEAT_INTERVAL)

    def heartbeat_listener(self):
        sock = udp_socket("", HEARTBEAT_PORT_BASE + self.id)
        while True:
            data, _ = sock.recvfrom(1024)
            msg = json.loads(data.decode())
            if msg["type"] == HEARTBEAT:
                self.last_heartbeat = time.time()

    def monitor_leader(self):
        while True:
            if not self.is_leader:
                if time.time() - self.last_heartbeat > HEARTBEAT_TIMEOUT:
                    print(f"[SERVER {self.id}] Leader dead")
                    self.start_election()
            time.sleep(1)

    # ---------------- START ----------------
    def start(self):
        threading.Thread(target=self.discovery_listener, daemon=True).start()
        time.sleep(1)
        self.discover_servers()

        threading.Thread(target=self.election_listener, daemon=True).start()
        threading.Thread(target=self.heartbeat_listener, daemon=True).start()
        threading.Thread(target=self.heartbeat_sender, daemon=True).start()
        threading.Thread(target=self.monitor_leader, daemon=True).start()

        if not self.servers:
            self.become_leader()
        else:
            self.start_election()

        while True:
            time.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--ip", required=True)
    args = parser.parse_args()

    Server(args.id, args.ip).start()
