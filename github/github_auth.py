import jwt
import time
import os
import requests


APP_ID = os.environ.get("GITHUB_APP_ID", "4365050")

INSTALLATION_ID = os.environ.get("GITHUB_INSTALLATION_ID", "148257662")


def generate_jwt():

    private_key = os.environ.get("GITHUB_PRIVATE_KEY", "")

    if not private_key:
        raise ValueError(
            "GITHUB_PRIVATE_KEY environment variable is not set."
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