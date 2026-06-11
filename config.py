import os
import secrets
from datetime import timedelta

AGENT_CAPTCHA_SECRET = os.environ.get(
    "AGENT_CAPTCHA_SECRET",
    secrets.token_urlsafe(32)
)

raw_sitekeys = os.environ.get("AGENT_CAPTCHA_SITEKEYS", "default_sitekey,test_sitekey")
AGENT_CAPTCHA_SITEKEYS = {k.strip() for k in raw_sitekeys.split(",") if k.strip()}

TOKEN_EXPIRY = timedelta(minutes=5)
USED_TOKENS = set()

BIND_HOST = os.environ.get("AGENT_CAPTCHA_HOST", "127.0.0.1")
BIND_PORT = int(os.environ.get("AGENT_CAPTCHA_PORT", "5200"))

BASE_URL = os.environ.get("AGENT_CAPTCHA_BASE_URL", "http://localhost:5200").rstrip("/")
