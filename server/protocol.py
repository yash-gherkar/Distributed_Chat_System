# server/protocol.py

# Client ↔ Leader
CLIENT_JOIN = "CLIENT_JOIN"     #client announces itself
#list the chatroom list
LIST_CHATROOMS = "LIST_CHATROOMS" 
CHATROOMS_LIST = "CHATROOMS_LIST"
CREATE_CHATROOM = "CREATE_CHATROOM"
JOIN_CHATROOM = "JOIN_CHATROOM"
ROOM_ASSIGNMENT = "ROOM_ASSIGNMENT"

# Client ↔ Chatroom Server
#JOIN_ACK = "JOIN_ACK"           #client acknowledges joining chatroom
CHAT_MSG = "CHAT_MSG"           #send chat message
ACK = "ACK"                     #client acknowldges message
DELIVERED = "DELIVERED"         #server confirms delivery
RESEND_REQUEST = "RESEND_REQUEST"   #server asks sender to resend

# Server ↔ Server
SERVER_UP = "SERVER_UP"         #new server joined
SERVER_SYNC = "SERVER_SYNC"     #Leader sends full state
HEARTBEAT = "HEARTBEAT"         #server heartbeat
ELECTION = "ELECTION"           #election trigger
LEADER_ANNOUNCE = "LEADER_ANNOUNCE" #new leader announced
ROOM_ASSIGNMENT_UPDATE = "ROOM_ASSIGNMENT_UPDATE" #Sync room ownership
