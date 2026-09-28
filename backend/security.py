import base64, hashlib, hmac, json, secrets, time
from fastapi import HTTPException, status
from backend.config import settings

_ITERATIONS = 310_000

def ensure_secret():
    if len(settings.app_secret) < 32:
        if settings.app_env == "production":
            raise RuntimeError("APP_SECRET must be set to a random value of at least 32 characters in production")
        settings.app_secret = secrets.token_urlsafe(48)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, expected = encoded.split("$")
        if scheme != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds))
        return hmac.compare_digest(base64.urlsafe_b64encode(actual).decode(), expected)
    except (ValueError, TypeError): return False

def issue_token(user_id: int) -> str:
    ensure_secret()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user_id, "exp": int(time.time()) + settings.access_token_minutes*60}, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.app_secret.encode(), payload.encode(), hashlib.sha256).digest()
    return payload + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")

def read_token(token: str) -> int:
    ensure_secret()
    try:
        payload, sig = token.split(".")
        expected = hmac.new(settings.app_secret.encode(), payload.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))): raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) < int(time.time()): raise ValueError()
        return int(data["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired bearer token", headers={"WWW-Authenticate":"Bearer"})

def new_device_key() -> str: return secrets.token_urlsafe(32)
def hash_device_key(key: str) -> str: return hashlib.sha256(key.encode()).hexdigest()
