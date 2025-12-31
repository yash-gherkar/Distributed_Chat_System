
# server/state.py
import time

class ServerState:
    def __init__(self, server_id):
        self.server_id = server_id

        self.is_leader = False
        self.leader_addr = None

        self.servers = {}      # server_id -> (ip, port)
        self.clients = {}      # client_id -> (ip, port)
        self.chatrooms = {}    # room_id -> set(client_id)
        self.server_load = {}  # server_id -> number of rooms hosted
        self.local_rooms = {} # room_name -> set(client_id) (ONLY rooms hosted here)

        self.pending_acks = {} # msg_id -> ack tracking

        self.last_heartbeat = time.time()
