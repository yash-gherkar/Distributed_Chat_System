# server/state.py
import time

class ServerState:
    def __init__(self, server_id):
        self.server_id = server_id

        self.is_leader = False
        self.leader_addr = None

        self.servers = {}      # server_id -> (ip, port)
        self.clients = {}      # client_id -> (ip, port)
        self.chatrooms = {}    # room_name -> server_id
        self.server_load = {}  # server_id -> number of rooms assigned
        self.local_rooms = {}  # room_name -> set(client_id) (rooms hosted on this server)

        self.pending_acks = {} # msg_id -> ack tracking

        self.last_heartbeat = time.time()
