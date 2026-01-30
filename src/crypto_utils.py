from cryptography.fernet import Fernet
from flask import current_app

def encrypt_token(token_str):
    if not token_str:
        return None
    # Ensure key is bytes
    key = current_app.config['ENCRYPTION_KEY']
    if not key:
        # In dev, maybe we want to fallback or error. Let's error to be safe.
        raise ValueError("ENCRYPTION_KEY not set in config")
    
    # Fernet key must be 32 url-safe base64-encoded bytes
    # If the user provided a string in env (likely), encode it.
    if isinstance(key, str):
        key = key.encode('utf-8')
        
    f = Fernet(key)
    return f.encrypt(token_str.encode('utf-8'))

def decrypt_token(token_bytes):
    if not token_bytes:
        return None
    key = current_app.config['ENCRYPTION_KEY']
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in config")
        
    if isinstance(key, str):
        key = key.encode('utf-8')

    f = Fernet(key)
    return f.decrypt(token_bytes).decode('utf-8')
