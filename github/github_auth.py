import jwt
import time
import os
import base64
import requests


APP_ID = os.environ.get("GITHUB_APP_ID", "4365050")

INSTALLATION_ID = os.environ.get("GITHUB_INSTALLATION_ID", "148257662")


def generate_jwt():

    # Support both GITHUB_APP_PRIVATE_KEY (base64) and GITHUB_PRIVATE_KEY (raw PEM)
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")

    if private_key:
        # Decode from base64 if it looks like base64 (doesn't start with ---)
        if not private_key.strip().startswith("-----"):
            try:
                private_key = base64.b64decode(private_key).decode("utf-8")
            except Exception:
                pass
    else:
        private_key = os.environ.get("GITHUB_PRIVATE_KEY", "")

    if not private_key:
        raise ValueError(
            "Neither GITHUB_APP_PRIVATE_KEY nor GITHUB_PRIVATE_KEY "
            "environment variable is set."
        )

    # Render env vars replace literal \n with \\n — fix that
    private_key = private_key.replace("\\n", "\n")

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "iss": APP_ID
    }

    encoded_jwt = jwt.encode(
        payload,
        private_key,
        algorithm="RS256"
    )

    return encoded_jwt


def generate_installation_token():

    jwt_token = generate_jwt()

    url = (
        "https://api.github.com/app/installations/"
        f"{INSTALLATION_ID}/access_tokens"
    )

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.post(
        url,
        headers=headers
    )

    response.raise_for_status()

    data = response.json()

    return data["token"]