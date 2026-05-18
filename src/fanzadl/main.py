import base64
import hashlib
import hmac
import json
import logging
import os

import requests

logger = logging.getLogger(__name__)


access_token = None
user_id = None


# region Helper functions
def truncate(data: str, trunc_len: int = 6) -> str:
    if len(data) > 2 * trunc_len:
        return f"{data[:trunc_len]}...{data[-trunc_len:]}"
    return data


def token_request(path: str, data: dict) -> requests.Response:
    return requests.post(
        f"{BASE_AUTH}{path}",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data=data,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=REQUEST_TIMEOUT,
    )


def first_value(dictionary):
    return next(iter(dictionary.values()))


def request_video(is_vr: bool, library_id: str, part: int, quality=None):
    authorization = f"Bearer {access_token}"
    if is_vr:
        signature = [
            authorization,
            library_id,
            exploit_id,
            USER_AGENT,
            quality,
            str(part),
        ]
    else:
        signature = [
            USER_AGENT,
            str(part),
            authorization,
            exploit_id,
            library_id,
        ]

    signature = hmac.new(
        SECRET_KEY.encode(), "".join(signature).encode(), hashlib.sha256
    ).hexdigest()
    response = requests.get(
        f"{BASE_VR}/playableprovider/stream/{'vr' if is_vr else '2d'}",
        params={
            "mylibrary_id": library_id,
            "part": part,
            "quality_group": quality,
        },
        headers={
            "x-api-auth-code": signature,
            "x-app-name": "oculus_quest2_vr",
            "x-app-ver": "v7.0.5",
            "x-authorization": authorization,
            "x-exploit-id": exploit_id,
            "x-user-agent": USER_AGENT,
        },
    )
    if response.status_code != 200:
        print(f"Request failed with status code {response.status_code}")
        print(response.text)
        raise Exception("Request failed")
    return response.json()


# endregion

# region Authentication
while access_token is None:
    if os.path.exists(REFRESH_TOKEN_PATH):
        with open(REFRESH_TOKEN_PATH) as f:
            refresh_token = f.read().strip()
        with open(USER_ID_PATH) as f:
            user_id = f.read().strip()
        print("Credentials OK!")

        access_token = token_request(
            "/connect/v1/token",
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if access_token.status_code == 200:
            access_token_data = access_token.json()
            access_token = access_token_data.get("body").get("access_token")
            new_refresh_token = access_token_data.get("body").get("refresh_token")
            if new_refresh_token is not None:
                with open(REFRESH_TOKEN_PATH, "w") as f:
                    f.write(new_refresh_token)
                break

        os.remove(REFRESH_TOKEN_PATH)
        print("Refresh token expired. Please re-authenticate.")

    print("Please input your DMM Credentials")

    email = input("Email: ")
    password = input("Password: ")

    response = token_request(
        "/connect/v1/token",
        data={
            "grant_type": "password",
            "email": email,
            "password": password,
        },
    )

    if response.status_code != 200:
        print("Login rejected. Are these credentials correct?")
        continue

    token_data = response.json()
    new_refresh_token = token_data.get("body").get("refresh_token")
    if new_refresh_token is None:
        print("Failed fetching refresh token, are these credentials valid?")
        continue
    with open(REFRESH_TOKEN_PATH, "w") as f:
        f.write(token_data.get("body").get("refresh_token"))
    with open(USER_ID_PATH, "w") as f:
        user_data = token_data.get("body").get("id_token").split(".")[1]
        user_data = json.loads(
            base64.b64decode(user_data + "=" * (4 - len(user_data) % 4))
        )
        f.write(user_data.get("user_id"))

print("Authentication successful!")
print(f"Access token: {truncate(access_token)}")

exploit_id = f"uid:{user_id}"


print()
print(f"Found {len(library)} items in the library.")
# endregion

# region Content selection
print("Which would you like to download?")
mappings = {}
for i, item in enumerate(library):
    print(f"{i + 1}. ({item.get('content_id')}) {item.get('title')}")
    mappings[item.get("content_id")] = i + 1
