import logging

from fanzadl.exceptions import AuthExpiredError
from fanzadl.functions import (
    auth_with_login,
    query_javstash_from_product_id,
    request,
    request_with_token,
)
from fanzadl.models.access import RefreshTokenDataModel
from fanzadl.models.library import (
    LibraryDataModel,
)
from fanzadl.models.video import (
    LibraryItemContentsModel,
    library_item_adapter,
)

logger = logging.getLogger(__name__)


class FanzaDLManager:
    def __init__(
        self,
        *,
        email: str | None = None,
        password: str | None = None,
        user_id: str | None = None,
        refresh_token: str | None = None,
        automatic_token_rotation: int | bool | None = True,
        javstash_api_key: str | None = None,
        auto_populate_library: bool = True,
    ) -> None:
        self.user_id: str
        self.refresh_token: str
        self.access_token: str

        self._process_auth_input(
            email=email,
            password=password,
            user_id=user_id,
            refresh_token=refresh_token,
        )

        _rotation = (
            0 if automatic_token_rotation is None else int(automatic_token_rotation)
        )
        if _rotation < 0:
            err = "automatic_token_rotation must be a non-negative integer or None"
            raise ValueError(err)
        self.automatic_token_rotation: int = _rotation

        self.javstash_api_key = javstash_api_key

        self.library: dict[int, LibraryItemContentsModel] = {}

        if auto_populate_library:
            self.update_library()

    def _process_auth_input(
        self,
        email: str | None,
        password: str | None,
        user_id: str | None,
        refresh_token: str | None,
    ) -> None:
        has_credentials = all(v is not None for v in (email, password))
        has_tokens = all(v is not None for v in (user_id, refresh_token))

        if has_credentials and has_tokens:
            err = "Provide either email/password or user_id/refresh_token, not both"
            raise ValueError(err)

        if not has_credentials and not has_tokens:
            err = "Must provide either email/password or user_id/refresh_token"
            raise ValueError(err)

        if has_credentials:
            # Using assert here to satisfy type checkers
            assert email is not None  # noqa: S101
            assert password is not None  # noqa: S101
            user_data, token_data = auth_with_login(email, password)
            self.user_id = user_data.user_id
            self.refresh_token = token_data.body.refresh_token
            self.access_token = token_data.body.access_token
        else:
            assert user_id is not None  # noqa: S101
            assert refresh_token is not None  # noqa: S101
            self.user_id = user_id
            self.refresh_token = refresh_token
            self.rotate_tokens()

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
        )

        access_token_response.raise_for_status()

        access_token_data = access_token_response.json()

        msg = f"Token rotation response: {access_token_data}"
        logger.debug(msg)

        if not isinstance(access_token_data, dict):
            err = f"Unexpected response format: {access_token_data}"
            raise TypeError(err)

        code = int(access_token_data["header"]["result_code"])
        if code != 0:
            err = f"Token rotation failed with code {code}: {access_token_data['body']}"
            raise AuthExpiredError(err)

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
    ) -> dict:
        try:
            return request(
                endpoint=endpoint,
                request_data=request_data,
                exploit_id=exploit_id,
                authorization=authorization,
            )
        except AuthExpiredError:
            for attempt in range(self.automatic_token_rotation):
                logger.info(
                    "Access token expired, rotating tokens (attempt %d/%d)...",
                    attempt + 1,
                    self.automatic_token_rotation,
                )
                self.rotate_tokens()
                try:
                    return request(
                        endpoint=endpoint,
                        request_data=request_data,
                        exploit_id=exploit_id,
                        authorization=self.authorization,
                    )
                except AuthExpiredError:
                    pass
            raise

    def update_library(self) -> None:
        page = 1

        new_library: dict[int, LibraryItemContentsModel] = {}
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
            )

            library_parsed = LibraryDataModel(**library_data)

            base_context = {
                "authorization": lambda: self.authorization,
                "exploit_id": lambda: self.exploit_id,
                "rotate_tokens": self.rotate_tokens,
                "max_rotation_retries": self.automatic_token_rotation,
                "mylibrary_id": None,
                "shop_name": None,
            }
            for elem in library_parsed.list_:
                context = {
                    **base_context,
                    "mylibrary_id": elem.contents["mylibrary_id"],
                    "shop_name": elem.contents["shop_name"],
                }

                model = library_item_adapter.validate_python(
                    elem.contents,
                    context=context,
                )

                if self.javstash_api_key is not None:
                    js_response = query_javstash_from_product_id(
                        model.content_id,
                        api_key=self.javstash_api_key,
                    )
                    scenes = js_response.data.query_scenes
                    if scenes.count == 1:
                        model.javstash_id = scenes.scenes[0].id
                        model.javstash_studio_code = scenes.scenes[0].code

                new_library[int(elem.contents["mylibrary_id"])] = model

            if len(new_library) >= library_parsed.content_total:
                break
            page += 1
        self.library = new_library
