try:
    import requests
except ImportError:
    print("The 'requests' library is not installed. Please install it with 'pip install requests'.")
    exit(1)

import argparse
import hmac
import os
import json
import hashlib
import urllib.parse
import base64

USER_AGENT = "DMMPLAY movie_player_plus (183, 5.2.10) API Level:34 PORTALAPP Android"
REFRESH_TOKEN_PATH = "refresh_token.txt"
USER_ID_PATH = "user_id.txt"
CSV_HEADER = "content,part,url"

BASE_AUTH = "https://gw.dmmapis.com"
BASE_API = "https://www.dmm.com"
BASE_VR = "https://vr.digapi.dmm.com"

CLIENT_ID = "xXGijBA7CVrsDZ5URBNKRVlHt2BqD5Ssyw3k0"
CLIENT_SECRET = "2FodTMUNOdzoNixyAojmwnDqICgNka83"

SECRET_KEY = "Ft8d3S8ElF6FG8QS"

profiles = {
    "video": {
        "device": "android",
        "appid": "android_movieplayer_app",
        "key": "hp2Y944L"
    },
    "vr": {
        "device": "vr",
        "appid": "android_movievrplayer_gear",
        "key": "0ZUlkiZe",
        "type": "oculusquest2"
    }
}

parser = argparse.ArgumentParser()
parser.add_argument(
    "--content-index",
    help="Automatically select the content to be downloaded by its content ID, or index in the library. Comma separated, supports ranges. Use '*' to download everything.",
    type=str
)
parser.add_argument(
    "--csv",
    help="Output stream URLs as a CSV file.",
    action="store_true"
)
parser.add_argument(
    "--output",
    help="Output stream URLs into a file.",
    type=str
)
parser.add_argument(
    "--vr-quality",
    help="Target quality for VR streams. 'highest' or 'lowest' also supported.",
    type=str,
    default="highest",
    choices=["highest", "lowest", "8k", "uhq", "hq", "12000", "6000", "4000"]
)
args = parser.parse_args()

print("""
  _____                    ____  _     
 |  ___|_ _ _ __  ______ _|  _ \\| |    
 | |_ / _` | '_ \\|_  / _` | | | | |    
 |  _| (_| | | | |/ / (_| | |_| | |___ 
 |_|  \\__,_|_| |_/___\\__,_|____/|_____|                         
""")
print("Credits: @PicoQubit on EMP")
print("License: GPL-3.0")
print()

access_token = None
user_id = None
exploit_id = None

#region Helper functions
def truncate(data, trunc_len=6):
    if len(data) > 2 * trunc_len:
        return f"{data[:trunc_len]}...{data[-trunc_len:]}"
    else:
        return data

def token_request(path, data=None):
    return requests.post(f"{BASE_AUTH}{path}", auth=(CLIENT_ID, CLIENT_SECRET), data=data, headers={
        "User-Agent": USER_AGENT,
    })

def request(endpoint, data={}, profile="video"):
    data["device"] = profiles[profile]["device"]
    data["HTTP_SMARTPHONE_APP"] = "DMM-APP"
    data["HTTP_USER_AGENT"] = USER_AGENT
    data["exploit_id"] = exploit_id

    if "type" in profiles[profile]:
        data["vr_appli_type"] = profiles[profile]["type"]

    body = json.dumps(data)
    signature = hmac.new(profiles[profile]["key"].encode(), body.encode(), hashlib.sha256).hexdigest()

    response = requests.post(f"{BASE_API}/service/digitalapi/-/json/=/method=PcApp/", headers={
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {access_token}",
    }, data={
        "authkey": signature,
        "appid": profiles[profile]["appid"],
        "message": endpoint,
        "params": body,
    })

    data = response.json()

    if "faultCode" in data:
        print(f"Request failed with faultCode {data.get('faultCode')}")
        print(f"faultString: {data.get('faultString')}")
        print(f"Endpoint: {endpoint}")
        print(f"Data: {data}")
        print(response.text)
        raise Exception("Request failed")
    
    return data.get("data")

def parse_ranges(ranges, mappings):
    if ranges == "*":
        for i in range(len(mappings)):
            yield i + 1
        return
    
    ranges = ranges.split(",")
    def to_number(x):
        if x.isnumeric():
            return int(x)
        else:
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

def first_value(dictionary):
    return next(iter(dictionary.values()))

def request_video(is_vr, library_id, part, quality=None):
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
    
    signature = hmac.new(SECRET_KEY.encode(), "".join(signature).encode(), hashlib.sha256).hexdigest()
    response = requests.get(f"{BASE_VR}/playableprovider/stream/{'vr' if is_vr else '2d'}", params={
        "mylibrary_id": library_id,
        "part": part,
        "quality_group": quality,
    }, headers = {
        "x-api-auth-code": signature,
        "x-app-name": "oculus_quest2_vr",
        "x-app-ver": "v7.0.5",
        "x-authorization": authorization,
        "x-exploit-id": exploit_id,
        "x-user-agent": USER_AGENT,
    })
    if response.status_code != 200:
        print(f"Request failed with status code {response.status_code}")
        print(response.text)
        raise Exception("Request failed")
    return response.json()
#endregion

#region Authentication
while access_token is None:
    if os.path.exists(REFRESH_TOKEN_PATH):
        with open(REFRESH_TOKEN_PATH, "r") as f:
            refresh_token = f.read().strip()
        with open(USER_ID_PATH, "r") as f:
            user_id = f.read().strip()
        print("Credentials OK!")

        access_token = token_request("/connect/v1/token", {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })
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

    response = token_request(f"/connect/v1/token", data={
        "grant_type": "password",
        "email": email,
        "password": password,
    })

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
        user_data = json.loads(base64.b64decode(user_data + "=" * (4 - len(user_data) % 4)))
        f.write(user_data.get("user_id"))

print("Authentication successful!")
print(f"Access token: {truncate(access_token)}")

exploit_id = f"uid:{user_id}"
#endregion

#region Library retrieval
library = []
page = 1

while True:
    library_data = request("Digital_Api_v2_Mylibrary.getList", {
        "vr_view_flag":1,
        "marking":"0",
        "limit":20,
        "page":page,
        "sort":"DESC",
    })
    library.extend(list(map(lambda x: x.get("contents"), library_data.get("list"))))
    if len(library) >= library_data.get("content_total"):
        break
    page += 1

print()
print(f"Found {len(library)} items in the library.")
#endregion

#region Content selection
print("Which would you like to download?")
mappings = {}
for i, item in enumerate(library):
    print(f"{i+1}. ({item.get('content_id')}) {item.get('title')}")
    mappings[item.get('content_id')] = i + 1

choices = args.content_index if args.content_index is not None else input("Comma separated list of indices to download, supports ranges (e.g. '1,3-5,7'): ")

print()
#endregion

#region URL retrieval
if args.output:
    with open(args.output, "w") as f:
        f.write((CSV_HEADER + "\n") if args.csv else "")
if args.csv:
    print(CSV_HEADER)

for choice in parse_ranges(choices, mappings):
    item = library[choice-1]

    item_detail = request("Digital_Api_Mylibrary.getDetail", {
        "mylibrary_id": item.get("mylibrary_id"),
        "product_id": item.get("product_id"),
        "shop_name": item.get("shop_name")
    })

    is_vr = item_detail.get("content_type") == "vr"

    if is_vr:
        pattern_data = item_detail.get("vr_rate_pattern").get("oculusquest2_vr")
        subpattern_data = pattern_data.get("stream")
        if args.vr_quality == "highest":
            bitrate_data = subpattern_data[-1]
        elif args.vr_quality == "lowest":
            bitrate_data = subpattern_data[0]
        else:
            bitrate_data = next(filter(lambda x: str(x.get("quality")) == args.vr_quality, subpattern_data))
    else:
        pattern_data = item_detail.get("rate_pattern").get("pc_pattern")
        subpattern_data = first_value(pattern_data).get("st")
        bitrate_data = subpattern_data.get("bitrate").get("0")

    part_count = bitrate_data.get("part")

    for part in range(0, part_count):
        """
        url_data = request("Digital_Api_Proxy.getURLPast", {
            "android_drm": False,
            "bitrate": "0",
            "drm": False,
            "chrome_cast": False,
            "isTablet": False,
            "licenseUID": license_uid,
            "product_id": product_id,
            "parent_product_id": item.get("product_id"),
            "transfer_type": "stream",
            "smartphone_access": False,
            "shop": item.get("shop_name"),
            "service": "digital",
            "part": str(part + 1),
        })
        url = url_data.get('redirect')
        """

        url_data = request_video(is_vr, item.get("mylibrary_id"), part + 1, bitrate_data.get("quality_group"))
        url = url_data.get('content_info').get("redirect")
        final_url = f"{url}&{url_data.get('cookie_info').get('name')}={urllib.parse.quote(str(url_data.get('cookie_info').get('value')))}&smartphone_access=1"

        formatted_entry = final_url
        if args.csv:
            formatted_entry = f"{item.get('content_id')},{part + 1},{final_url}"

        print(formatted_entry)
        if args.output:
            with open(args.output, "a") as f:
                f.write(formatted_entry + "\n")
#endregion
