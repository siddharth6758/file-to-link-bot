import json
import time
import os
from cryptography.fernet import Fernet

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set")

fernet = Fernet(SECRET_KEY.encode())
TTL = 300  # 5 minutes


def generate_token(file_id: str, media_type: str) -> str:
    payload = {
        "file_id": file_id,
        "media_type": media_type,
        "exp": time.time() + TTL
    }
    return fernet.encrypt(json.dumps(payload).encode()).decode()


def verify_token(token: str):
    try:
        data = json.loads(fernet.decrypt(token.encode()).decode())
        if data["exp"] < time.time():
            return None
        return data
    except Exception:
        return None