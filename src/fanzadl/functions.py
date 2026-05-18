import hmac
import json
import logging
from collections.abc import Iterator
from typing import Literal

import requests

from fanzadl.constants import PROFILES, USER_AGENT

logger = logging.getLogger(__name__)


def parse_ranges(ranges: str, mappings: dict) -> Iterator[int]:
    if ranges == "*":
        for i in range(len(mappings)):
            yield i + 1
        return

    ranges = ranges.split(",")

    def to_number(x: str):
        if x.isnumeric():
            return int(x)
        return mappings.get(x)

    for part in ranges:
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start = to_number(start)
            end = to_number(end)
            if start is None or end is None:
                print(f"Invalid range: {part}")
                exit(1)
            for i in range(start, end + 1):
                yield i
        else:
            yield to_number(part)


def get_library() -> list[str]:
    library = []
    page = 1

    while True:
        library_data = request(
            "Digital_Api_v2_Mylibrary.getList",
            {
                "vr_view_flag": 1,
                "marking": "0",
                "limit": 20,
                "page": page,
                "sort": "DESC",
            },
        )
        library.extend(list(map(lambda x: x.get("contents"), library_data.get("list"))))
        if len(library) >= library_data.get("content_total"):
            break
        page += 1

    return library


def request(
    endpoint: str, data: dict | None = None, profile: Literal["video"] = "video"
) -> requests.Response:
    if data is None:
        data = {}

    data["device"] = PROFILES[profile]["device"]
    data["HTTP_SMARTPHONE_APP"] = "DMM-APP"
    data["HTTP_USER_AGENT"] = USER_AGENT
    data["exploit_id"] = exploit_id

    if "type" in PROFILES[profile]:
        data["vr_appli_type"] = PROFILES[profile]["type"]

    body = json.dumps(data)
    signature = hmac.new(
        profiles[profile]["key"].encode(), body.encode(), hashlib.sha256
    ).hexdigest()

    response = requests.post(
        f"{BASE_API}/service/digitalapi/-/json/=/method=PcApp/",
        headers={
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {access_token}",
        },
        data={
            "authkey": signature,
            "appid": profiles[profile]["appid"],
            "message": endpoint,
            "params": body,
        },
        timeout=REQUEST_TIMEOUT,
    )

    data = response.json()

    if "faultCode" in data:
        msg = f"""Request failed with faultCode {data.get("faultCode")}
            faultString: {data.get("faultString")}
            Endpoint: {endpoint}
            Data: {data}
            response.text
            """
        logger.error(msg)
        raise Exception("Request failed")

    return data.get("data")
