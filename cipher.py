# cipher.py
import base64

# A simple "lightweight" key for our XOR cipher
KEY = "STUTTGART"

def transform(text, key=KEY):
    """Simple XOR transformation for basic encryption/decryption."""
    result = ""
    for i in range(len(text)):
        # XOR the character with a character from the key
        result += chr(ord(text[i]) ^ ord(key[i % len(key)]))
    return result

def encrypt(text):
    """Encrypts text and returns a base64 string (to avoid UDP transmission errors)."""
    ciphered = transform(text)
    return base64.b64encode(ciphered.encode()).decode()

def decrypt(token):
    """Decodes base64 and reverses the XOR transformation."""
    ciphered = base64.b64decode(token.encode()).decode()
    return transform(ciphered)