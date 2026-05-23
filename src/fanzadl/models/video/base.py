import urllib
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date, datetime
from typing import Literal

import requests
from pydantic import HttpUrl, PrivateAttr, ValidationInfo, model_validator

from fanzadl.constants import BASE_VR, USER_AGENT
from fanzadl.exceptions import RequestError
from fanzadl.functions import request
from fanzadl.models.response import VideoResponseModel
from fanzadl.models.strict import StrictBaseModel


class RatePatternModel(StrictBaseModel):
    is_sp_hdst: bool
    is_sp_hddl: bool


class _AuthAwareModel(StrictBaseModel):
    _get_authorization: Callable[[], str] = PrivateAttr()
    _get_exploit_id: Callable[[], str] = PrivateAttr()

    @model_validator(mode="after")
    def inject_callable(self, info: ValidationInfo) -> "_AuthAwareModel":
        if info.context:
            if "authorization" in info.context:
                self._get_authorization = info.context["authorization"]
            if "exploit_id" in info.context:
                self._get_exploit_id = info.context["exploit_id"]

        return self

    @property
    def authorization(self) -> str:
        return self._get_authorization()

    @property
    def exploit_id(self) -> str:
        return self._get_exploit_id()


class _LibraryIDAwareModel(StrictBaseModel):
    _mylibrary_id: int = PrivateAttr(default=0)

    @model_validator(mode="after")
    def get_mylibrary_id(self, info):
        if info.context and "mylibrary_id" in info.context:
            self._mylibrary_id = info.context["mylibrary_id"]
        return self

    @property
    def mylibrary_id(self) -> int:
        return self._mylibrary_id


class _BaseLibraryItemContentsModel(_AuthAwareModel):
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

    def get_detail(self, *, timeout: int = 60) -> dict:
        return request(
            endpoint="Digital_Api_Mylibrary.getDetail",
            authorization=self.authorization,
            exploit_id=self.exploit_id,
            request_data={
                "mylibrary_id": self.mylibrary_id,
                "product_id": self.product_id,
                "shop_name": self.shop_name,
            },
            timeout=timeout,
        )


class _BaseQualityModel(_AuthAwareModel, _LibraryIDAwareModel, ABC):
    fps: float
    quality_display_name: str
    quality_group: str
    quality_order: int
    url_suffix: Literal["2d", "vr"]

    @abstractmethod
    def build_signature(self, *, part: int) -> str: ...

    def request_part(self, part: int, *, timeout: int = 60) -> VideoResponseModel:
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
            timeout=timeout,
        )

        response.raise_for_status()
        js = response.json()

        if not isinstance(js, dict):
            err = "Unexpected response format"
            raise TypeError(err)

        out = VideoResponseModel(**js)
        if out.status.code != 0:
            err = f"Error in response: {out.status}"
            raise RequestError(err)

        return out

    def get_url(self, part: int, *, timeout: int = 60) -> str:
        response = self.request_part(
            part=part,
            timeout=timeout,
        )
        content_info = response.content_info
        cookie_info = response.cookie_info
        return f"{content_info.redirect}&{cookie_info.name}={urllib.parse.quote(str(cookie_info.value))}&smartphone_access=1"
