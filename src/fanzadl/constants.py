USER_AGENT = "DMMPLAY movie_player_plus (183, 5.2.10) API Level:34 PORTALAPP Android"
REFRESH_TOKEN_PATH = "refresh_token.txt"  # noqa: S105

BASE_AUTH = "https://gw.dmmapis.com"
BASE_API = "https://www.dmm.com"
BASE_VR = "https://vr.digapi.dmm.com"

CLIENT_ID = "xXGijBA7CVrsDZ5URBNKRVlHt2BqD5Ssyw3k0"
CLIENT_SECRET = "2FodTMUNOdzoNixyAojmwnDqICgNka83"  # noqa: S105

SECRET_KEY = "Ft8d3S8ElF6FG8QS"  # noqa: S105
REQUESTS_TIMEOUT = 60


PROFILES = {
    "video": {
        "device": "android",
        "appid": "android_movieplayer_app",
        "key": "hp2Y944L",
    },
    "vr": {
        "device": "vr",
        "appid": "android_movievrplayer_gear",
        "key": "0ZUlkiZe",
        "type": "oculusquest2",
    },
}

JAVSTASH_GRAPHQL_ENDPOINT = "https://javstash.org/graphql"
