import time

class ServerState:
    def __init__(self, server_id):
        self.server_id = server_id

        self.is_leader = False
        self.leader_id = None
        self.leader_addr = None

        self.servers = {}          # server_id -> (ip, port)
        self.clients = {}          # client_id -> (ip, port)
        self.chatrooms = {}        # room -> owner server_id
        self.server_load = {}      # server_id -> room count
        self.local_rooms = {}      # room -> set(client_id)

        self.last_heartbeat = time.time()
