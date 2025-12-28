# server/utils.py
import uuid
import time

def generate_msg_id():
    return str(uuid.uuid4())

def now():
    return time.time()
