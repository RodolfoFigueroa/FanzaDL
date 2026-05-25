import base64
import hashlib
import hmac
import json
import logging

import requests

from fanzadl.constants import (
    BASE_API,
    BASE_AUTH,
    CLIENT_ID,
    CLIENT_SECRET,
    PROFILES,
    SECRET_KEY,
    USER_AGENT,
)
from fanzadl.exceptions import AuthExpiredError, RequestError
from fanzadl.models.access import AccessTokenDataModel
from fanzadl.models.user import UserDataModel

logger = logging.getLogger(__name__)


def get_library_mappings(library: list[dict]) -> dict:
    mappings = {}
    for i, item in enumerate(library):
        print(f"{i + 1}. ({item.get('content_id')}) {item.get('title')}")
        mappings[item.get("content_id")] = i + 1
    return mappings


def request_with_token(
    path: str, data: dict, *, timeout: int = 60
) -> requests.Response:
    return requests.post(
        f"{BASE_AUTH}{path}",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data=data,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=timeout,
    )


def auth_with_login(
    email: str, password: str, *, timeout: int = 60
) -> tuple[UserDataModel, AccessTokenDataModel]:
    response = request_with_token(
        "/connect/v1/token",
        data={
            "grant_type": "password",
            "email": email,
            "password": password,
        },
        timeout=timeout,
    )

    response.raise_for_status()

    token_data = response.json()

    if not isinstance(token_data, dict):
        err = f"Unexpected response format: {token_data}"
        raise TypeError(err)

    validated_token_data = AccessTokenDataModel(**token_data)

    user_data_str = validated_token_data.body.id_token.split(".")[1]
    user_data: dict = json.loads(
        base64.b64decode(user_data_str + "=" * (4 - len(user_data_str) % 4))
    )
    return UserDataModel(**user_data), validated_token_data


def request(
    endpoint: str,
    *,
    request_data: dict,
    exploit_id: str,
    authorization: str,
    timeout: int = 60,
) -> dict:
    profile = PROFILES["video"]

    request_data["device"] = profile["device"]
    request_data["HTTP_SMARTPHONE_APP"] = "DMM-APP"
    request_data["HTTP_USER_AGENT"] = USER_AGENT
    request_data["exploit_id"] = exploit_id

    if "type" in profile:
        request_data["vr_appli_type"] = profile["type"]

    body = json.dumps(request_data)
    signature = hmac.new(
        profile["key"].encode(), body.encode(), hashlib.sha256
    ).hexdigest()

    response = requests.post(
        f"{BASE_API}/service/digitalapi/-/json/=/method=PcApp/",
        headers={
            "User-Agent": USER_AGENT,
            "Authorization": authorization,
        },
        data={
            "authkey": signature,
            "appid": profile["appid"],
            "message": endpoint,
            "params": body,
        },
        timeout=timeout,
    )

    response.raise_for_status()

    response_json = response.json()
    if not isinstance(response_json, dict):
        err = f"Unexpected response format: {response_json}"
        raise TypeError(err)

    if not response_json["event"]:
        error_code = response_json.get("error", "Unknown error")
        if error_code == "E210013":
            raise AuthExpiredError

        err = f"API error: {error_code} | Message: {response_json.get('message', 'No message')}"
        raise RequestError(err)

    out = response_json["data"]
    if not isinstance(out, dict):
        err = f"Unexpected data format: {out}"
        raise TypeError(err)

    return out


def hash_signature(signature: list[str]) -> str:
    return hmac.new(
        SECRET_KEY.encode(), "".join(signature).encode(), hashlib.sha256
    ).hexdigest()
