# state.py
import socket
import time

BROADCAST_PORT = 10001
ELECTION_PORT_BASE = 11000
HEARTBEAT_PORT_BASE = 12000
CLIENT_PORT = 13000

HEARTBEAT_INTERVAL = 2
HEARTBEAT_TIMEOUT = 5


def udp_socket(bind_ip=None, bind_port=None, broadcast=False, timeout=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if broadcast:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if bind_ip is not None:
        s.bind((bind_ip, bind_port))
    if timeout:
        s.settimeout(timeout)
    return s
