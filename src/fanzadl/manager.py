import logging

import requests

from fanzadl.exceptions import AuthExpiredError
from fanzadl.functions import auth_with_login, request, request_with_token
from fanzadl.models.access import RefreshTokenDataModel
from fanzadl.models.library import (
    LibraryDataModel,
)
from fanzadl.models.video import (
    VideoLibraryItemContentsModel,
    VRLibraryItemContentsModel,
)
from fanzadl.models.video.base import _BaseLibraryItemContentsModel

logger = logging.getLogger(__name__)


class FanzaDLManager:
    def __init__(
        self,
        email: str,
        password: str,
        *,
        request_timeout: int = 60,
        automatic_token_rotation: bool = True,
    ) -> None:
        self.email = email
        self.password = password
        self.request_timeout = request_timeout
        self.automatic_token_rotation = automatic_token_rotation

        user_data, token_data = auth_with_login(
            email, password, timeout=self.request_timeout
        )

        self.user_id = user_data.user_id
        self.refresh_token = token_data.body.refresh_token
        self.access_token = token_data.body.access_token

        self.library: dict[
            int, VideoLibraryItemContentsModel | VRLibraryItemContentsModel
        ] = {}
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
            raise AuthExpiredError from e

        access_token_data = access_token_response.json()

        if not isinstance(access_token_data, dict):
            err = f"Unexpected response format: {access_token_data}"
            raise TypeError(err)

        token_data = RefreshTokenDataModel(**access_token_data)
        self.access_token = token_data.body.access_token
        self.refresh_token = token_data.body.refresh_token

    def _request_with_auto_rotation(
        self,
        endpoint: str,
        *,
        request_data: dict,
        exploit_id: str,
        authorization: str,
        timeout: int = 60,
    ) -> dict:
        try:
            return request(
                endpoint=endpoint,
                request_data=request_data,
                exploit_id=exploit_id,
                authorization=authorization,
                timeout=timeout,
            )
        except AuthExpiredError:
            if self.automatic_token_rotation:
                logger.info("Access token expired, rotating tokens...")
                self.rotate_tokens()
                return request(
                    endpoint=endpoint,
                    request_data=request_data,
                    exploit_id=exploit_id,
                    authorization=self.authorization,
                    timeout=timeout,
                )
            raise

    # TODO: This depends on the assumption that the auth token is valid for the entire
    # duration of the library update, since each item needs it to build its
    # `details` property. If token expiration becomes an issue, consider implementing
    # a more robust token management strategy, such as checking token validity
    # before each request and rotating if necessary.
    def update_library(self) -> None:
        page = 1

        while True:
            library_data = self._request_with_auto_rotation(
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

            base_context = {
                "authorization": lambda: self.authorization,
                "exploit_id": lambda: self.exploit_id,
                "mylibrary_id": None,
                "shop_name": None,
            }
            for elem in library_parsed.list_:
                context = {
                    **base_context,
                    "mylibrary_id": elem.contents["mylibrary_id"],
                    "shop_name": elem.contents["shop_name"],
                    "product_id": elem.contents["product_id"],
                }

                if elem.contents["content_type"] == "video":
                    # Create a temporary _BaseLibraryItemContentsModel to
                    # extract the details field
                    _temp_contents = elem.contents.copy()
                    del _temp_contents["content_type"]
                    _base_model = _BaseLibraryItemContentsModel.model_validate(
                        _temp_contents,
                        context=context,
                    )

                    # Inject the delivery_content_info into the contents for
                    # the final model validation
                    elem.contents["video_list"] = _base_model.details[
                        "delivery_content_info"
                    ]

                    model = VideoLibraryItemContentsModel.model_validate(
                        elem.contents,
                        context=context,
                    )
                elif elem.contents["content_type"] == "vr":
                    model = VRLibraryItemContentsModel.model_validate(
                        elem.contents,
                        context=context,
                    )
                else:
                    err = f"Unknown content type: {elem.contents['content_type']}"
                    raise ValueError(err)

                self.library[int(elem.contents["mylibrary_id"])] = model

            if len(self.library) >= library_parsed.content_total:
                break
            page += 1
