import urllib.parse
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date, datetime
from functools import cached_property
from typing import Generic, Literal, Self, TypeVar
from uuid import UUID

import requests
from pydantic import (
    ConfigDict,
    Field,
    HttpUrl,
    PrivateAttr,
    SecretStr,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from fanzadl.constants import BASE_VR, REQUESTS_TIMEOUT, USER_AGENT
from fanzadl.exceptions import AuthExpiredError, RequestError
from fanzadl.functions import query_javstash_from_product_id, request
from fanzadl.models.response import VideoResponseModel
from fanzadl.models.strict import StrictBaseModel


class RatePatternModel(StrictBaseModel):
    is_sp_hdst: bool
    is_sp_hddl: bool


class _AuthAwareModel(StrictBaseModel):
    _get_authorization: Callable[[], str] = PrivateAttr()
    _get_exploit_id: Callable[[], str] = PrivateAttr()
    _rotate_tokens: Callable[[], None] | None = PrivateAttr(default=None)
    _max_rotation_retries: int = PrivateAttr(default=0)

    @model_validator(mode="after")
    def inject_callable(self, info: ValidationInfo) -> Self:
        if info.context:
            if "authorization_callback" in info.context:
                self._get_authorization = info.context["authorization_callback"]
            if "exploit_id_callback" in info.context:
                self._get_exploit_id = info.context["exploit_id_callback"]
            if "rotate_tokens_callback" in info.context:
                self._rotate_tokens = info.context["rotate_tokens_callback"]
            if "max_rotation_retries" in info.context:
                self._max_rotation_retries = info.context["max_rotation_retries"]

        return self

    @property
    def authorization(self) -> str:
        return self._get_authorization()

    @property
    def exploit_id(self) -> str:
        return self._get_exploit_id()


class _LibraryPropertiesAwareModel(StrictBaseModel):
    _mylibrary_id: int = PrivateAttr(default=0)
    _shop_name: str = PrivateAttr(default="")

    @model_validator(mode="after")
    def get_library_properties(self, info: ValidationInfo) -> Self:
        if info.context:
            if "mylibrary_id" in info.context:
                self._mylibrary_id = info.context["mylibrary_id"]
            if "shop_name" in info.context:
                self._shop_name = info.context["shop_name"]
        return self

    @property
    def mylibrary_id(self) -> int:
        return self._mylibrary_id

    @property
    def shop_name(self) -> str:
        return self._shop_name


class _BaseQualityModel(_AuthAwareModel, _LibraryPropertiesAwareModel, ABC):
    model_config = ConfigDict(populate_by_name=True)

    fps: float
    parts: int = Field(alias="part")
    quality_display_name: str
    quality_group: str
    quality_order: int
    url_suffix: Literal["2d", "vr"]

    @abstractmethod
    def build_signature(self, *, part: int) -> str: ...

    def _do_request_part(self, part: int) -> VideoResponseModel:
        signature = self.build_signature(part=part)

        response = requests.get(
            f"{BASE_VR}/playableprovider/stream/{self.url_suffix}",
            params={
                "mylibrary_id": self.mylibrary_id,
                "part": part,
                "quality_group": self.quality_group,
            },
            headers={
                "x-api-auth-code": signature,
                "x-app-name": "oculus_quest2_vr",
                "x-app-ver": "v7.0.5",
                "x-authorization": self.authorization,
                "x-exploit-id": self.exploit_id,
                "x-user-agent": USER_AGENT,
            },
            timeout=REQUESTS_TIMEOUT,
        )

        response.raise_for_status()
        js = response.json()

        if not isinstance(js, dict):
            err = "Unexpected response format"
            raise TypeError(err)

        status_code = js["status"]["code"]
        if status_code != 0:
            if status_code == 401:
                raise AuthExpiredError
            err = f"Error in response: {js}"
            raise RequestError(err)

        out = VideoResponseModel(**js)
        if out.status.code != 0:
            err = f"Error in response: {out.status}"
            raise RequestError(err)

        return out

    def request_part(self, part: int) -> VideoResponseModel:
        try:
            return self._do_request_part(part)
        except AuthExpiredError:
            if self._rotate_tokens is not None:
                for _attempt in range(self._max_rotation_retries):
                    self._rotate_tokens()
                    try:
                        return self._do_request_part(part)
                    except AuthExpiredError:
                        pass
            raise

    def get_url(self, part: int) -> str:
        response = self.request_part(
            part=part,
        )
        content_info = response.content_info
        cookie_info = response.cookie_info
        return f"{content_info.redirect}&{cookie_info.name}={urllib.parse.quote(str(cookie_info.value))}&smartphone_access=1"

    def get_all_urls(self) -> list[str]:
        if self.parts == 0:
            return [self.get_url(part=0)]

        return [self.get_url(part=i) for i in range(1, self.parts + 1)]


QualityT = TypeVar("QualityT", bound=_BaseQualityModel, default=_BaseQualityModel)


class _BaseDeliveryInfoModel(
    _AuthAwareModel, _LibraryPropertiesAwareModel, Generic[QualityT]
):
    download: list[QualityT] = []  # noqa: RUF012
    stream: list[QualityT] = []  # noqa: RUF012

    @field_validator("download", "stream")
    @classmethod
    def enforce_sorted_quality(cls, v: list[QualityT] | None) -> list[QualityT] | None:
        if v is None:
            return v
        return sorted(v, key=lambda x: x.quality_order)

    @model_validator(mode="after")
    def enforce_at_least_one_quality(self) -> Self:
        if len(self.download) == 0 and len(self.stream) == 0:
            err = "At least one of download or stream must have quality information"
            raise ValueError(err)
        return self

    @model_validator(mode="after")
    def enforce_part_count(self) -> Self:
        part_counts = {
            quality.parts
            for delivery_method in (self.download, self.stream)
            for quality in delivery_method
        }

        if len(part_counts) > 1:
            err = f"Inconsistent part counts: {part_counts}"
            raise ValueError(err)

        return self

    @computed_field
    @property
    def parts(self) -> int:
        delivery = next(m for m in (self.download, self.stream) if m)
        return delivery[0].parts

    @computed_field
    @property
    def download_highest(self) -> QualityT | None:
        if len(self.download) == 0:
            return None
        return self.download[-1]

    @computed_field
    @property
    def stream_highest(self) -> QualityT | None:
        if len(self.stream) == 0:
            return None
        return self.stream[-1]

    @computed_field
    @property
    def highest(self) -> QualityT | None:
        candidates = [
            q for q in (self.download_highest, self.stream_highest) if q is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x.quality_order)


class _BaseRatePatternModel(
    _AuthAwareModel, _LibraryPropertiesAwareModel, Generic[QualityT]
):
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def enforce_equal_part_count(self) -> Self:
        part_counts = {delivery_info.parts for _, delivery_info in self}
        if len(part_counts) > 1:
            err = f"Inconsistent part counts across delivery methods: {part_counts}"
            raise ValueError(err)

        return self

    @computed_field
    @property
    def parts(self) -> int:
        _, delivery = next(iter(self))
        return delivery.parts

    @computed_field
    @property
    def download_highest(self) -> QualityT | None:
        dl_list: list[QualityT] = []
        for _, model in self:
            attr = model.download_highest
            if attr is not None:
                dl_list.append(attr)
        if len(dl_list) == 0:
            return None
        return max(dl_list, key=lambda x: x.quality_order)

    @computed_field
    @property
    def stream_highest(self) -> QualityT | None:
        dl_list: list[QualityT] = []
        for _, model in self:
            attr = model.stream_highest
            if attr is not None:
                dl_list.append(attr)
        if len(dl_list) == 0:
            return None
        return max(dl_list, key=lambda x: x.quality_order)

    @computed_field
    @property
    def highest(self) -> QualityT | None:
        candidates = [
            q for q in (self.download_highest, self.stream_highest) if q is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x.quality_order)


class _SkeletonLibraryItemContentsModel(_AuthAwareModel):
    _javstash_api_key: SecretStr | None = PrivateAttr(default=None)

    allow_foreign: int
    android_dl_flag: int
    approx_release_date: date | None
    begin: datetime
    content_id: str
    copyright: None
    delivery_begin: None
    delivery_info: dict | None = None
    device_delivery_flag: dict | None = None
    download_expire: int
    end: datetime
    expire: date
    grade: None
    iphone_dl_begin: None
    iphone_dl_flag: int
    iphone_st_begin: None
    is_enabled: bool
    is_stage_live_content_flag: bool
    is_stream_pack: int
    is_adult: bool
    license_expire_date: date | None
    license_expire_on_purchase: int | None
    live_begin: None
    live_end: None
    marking: int
    mylibrary_id: int
    package_image_url: HttpUrl
    pc_hddl_flag: bool
    pc_hdst_flag: bool
    play_begin: datetime
    product_id: str
    purchase_date: datetime
    rate_pattern: RatePatternModel
    rental_days: int | None
    reserve_flag: bool
    shop_name: Literal["videoa"]
    stream_expire: int
    title: str
    trans_type: Literal["download", "stream"]

    @model_validator(mode="after")
    def inject_javstash_api_key(self, info: ValidationInfo) -> Self:
        if info.context and "javstash_api_key" in info.context:
            key = info.context["javstash_api_key"]
            if key is not None:
                self._javstash_api_key = SecretStr(key)
        return self

    @cached_property
    def _javstash_info(self) -> dict | None:
        if self._javstash_api_key is None:
            return None
        js_response = query_javstash_from_product_id(
            self.content_id,
            api_key=self._javstash_api_key.get_secret_value(),
        )
        scenes = js_response.data.query_scenes
        if scenes.count != 1:
            err = f"Expected exactly one scene from JavStash for product_id {self.product_id}, got {scenes.count}"
            raise ValueError(err)

        return {
            "javstash_id": scenes.scenes[0].id,
            "javstash_studio_code": scenes.scenes[0].code,
        }

    @computed_field
    @property
    def javstash_id(self) -> UUID | None:
        return (
            self._javstash_info["javstash_id"]
            if self._javstash_info is not None
            else None
        )

    @computed_field
    @property
    def javstash_studio_code(self) -> str | None:
        return (
            self._javstash_info["javstash_studio_code"]
            if self._javstash_info is not None
            else None
        )


class _BaseLibraryItemContentsModel(
    _SkeletonLibraryItemContentsModel, Generic[QualityT]
):
    video_list: _BaseRatePatternModel[QualityT] | None = None

    @computed_field
    @cached_property
    def details(self) -> dict:
        return request(
            endpoint="Digital_Api_Mylibrary.getDetail",
            authorization=self.authorization,
            exploit_id=self.exploit_id,
            request_data={
                "mylibrary_id": self.mylibrary_id,
                "product_id": self.product_id,
                "shop_name": self.shop_name,
            },
        )

    @computed_field
    @property
    def parts(self) -> int:
        if self.video_list is None:
            err = "Video list is not available to determine part count."
            raise ValueError(err)
        return self.video_list.parts

    @computed_field
    @property
    def download_highest(self) -> QualityT | None:
        if self.video_list is None:
            err = "Video list is not available to determine highest download quality."
            raise ValueError(err)
        return self.video_list.download_highest

    @computed_field
    @property
    def stream_highest(self) -> QualityT | None:
        if self.video_list is None:
            err = "Video list is not available to determine highest stream quality."
            raise ValueError(err)
        return self.video_list.stream_highest

    @computed_field
    @property
    def highest(self) -> QualityT | None:
        candidates = [
            q for q in (self.download_highest, self.stream_highest) if q is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x.quality_order)
