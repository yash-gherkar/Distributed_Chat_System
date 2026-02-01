# client.py
import socket
import json
from protocol import *
from state import *

def main():
    sock = udp_socket(broadcast=True)
    sock.sendto(
        json.dumps({"type": CLIENT_JOIN}).encode(),
        ("255.255.255.255", BROADCAST_PORT)
    )

    sock = udp_socket("", CLIENT_PORT)
    data, _ = sock.recvfrom(1024)
    msg = json.loads(data.decode())
    print("Connected to leader:", msg)

if __name__ == "__main__":
    main()
