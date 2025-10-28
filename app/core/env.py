import os
from dotenv import load_dotenv, find_dotenv

# Load .env from project root (walks up directories)
load_dotenv(find_dotenv(), override=False)

def require(keys: list[str]) -> None:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
