# state.py
import time

class ServerState:
    def __init__(self, server_id):
        self.server_id = server_id
        self.is_leader = False
        self.leader_addr = None
        self.servers = {}      # server_id -> (ip, port)
        self.clients = {}      # client_id -> (ip, port)
        self.chatrooms = {}    # room -> list of client_ids
        self.room_assignment = {}  # room -> server_id
        self.server_load = {}  # server_id -> number of rooms assigned
        self.last_heartbeat = {}
