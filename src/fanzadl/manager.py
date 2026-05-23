import logging

import requests

from fanzadl.exceptions import AuthExpiredError
from fanzadl.functions import auth_with_login, request, request_with_token
from fanzadl.models.access import AccessTokenDataModel
from fanzadl.models.library import (
    LibraryDataModel,
)
from fanzadl.models.video import (
    VideoLibraryItemContentsModel,
    VRLibraryItemContentsModel,
)

logger = logging.getLogger(__name__)


class FanzaDLManager:
    def __init__(self, email: str, password: str, *, request_timeout: int = 60) -> None:
        self.email = email
        self.password = password
        self.request_timeout = request_timeout

        user_data, token_data = auth_with_login(
            email, password, timeout=self.request_timeout
        )

        self.user_id = user_data.user_id
        self.refresh_token = token_data.body.refresh_token
        self.access_token = token_data.body.access_token

        self.video_library: dict[str, VideoLibraryItemContentsModel] = {}
        self.vr_library: dict[str, VRLibraryItemContentsModel] = {}
        self.update_library()

    @property
    def exploit_id(self) -> str:
        return f"uid:{self.user_id}"

    @property
    def authorization(self) -> str:
        return f"Bearer {self.access_token}"

    def rotate_tokens(self) -> None:
        access_token_response = request_with_token(
            "/connect/v1/token",
            {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=self.request_timeout,
        )

        try:
            access_token_response.raise_for_status()
        except requests.HTTPError as e:
            err = "Refresh token expired"
            raise AuthExpiredError(err) from e

        access_token_data = access_token_response.json()

        if not isinstance(access_token_data, dict):
            err = f"Unexpected response format: {access_token_data}"
            raise TypeError(err)

        token_data = AccessTokenDataModel(**access_token_data)
        self.access_token = token_data.body.access_token
        self.refresh_token = token_data.body.refresh_token

    def update_library(self) -> None:
        page = 1

        while True:
            library_data = request(
                endpoint="Digital_Api_v2_Mylibrary.getList",
                request_data={
                    "vr_view_flag": 1,
                    "marking": "0",
                    "limit": 20,
                    "page": page,
                    "sort": "DESC",
                },
                exploit_id=self.exploit_id,
                authorization=self.authorization,
                timeout=self.request_timeout,
            )

            library_parsed = LibraryDataModel(**library_data)

            context = {
                "authorization": lambda: self.authorization,
                "exploit_id": lambda: self.exploit_id,
                "mylibrary_id": None,
            }
            for elem in library_parsed.list_:
                context["mylibrary_id"] = elem.contents["mylibrary_id"]

                if elem.contents["content_type"] == "video":
                    model = VideoLibraryItemContentsModel.model_validate(
                        elem.contents,
                        context=context,
                    )
                    self.video_library[elem.contents["mylibrary_id"]] = model
                elif elem.contents["content_type"] == "vr":
                    model = VRLibraryItemContentsModel.model_validate(
                        elem.contents,
                        context=context,
                    )
                    self.vr_library[elem.contents["mylibrary_id"]] = model
                else:
                    err = f"Unknown content type: {elem.contents['content_type']}"
                    raise ValueError(err)

            if (
                len(self.video_library) + len(self.vr_library)
                >= library_parsed.content_total
            ):
                break
            page += 1
