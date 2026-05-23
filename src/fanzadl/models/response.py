from datetime import datetime
from typing import Literal

from pydantic import HttpUrl

from fanzadl.models.strict import StrictBaseModel


class VideoResponseContentInfoModel(StrictBaseModel):
    content_id: str
    redirect: HttpUrl
    recommended_viewing_type: str | None = None


class VideoResponseCookieInfoModel(StrictBaseModel):
    name: Literal["licenseUID"]
    value: str
    expire: int
    path: Literal["/"]
    domain: Literal["dmm.com"]


class VideoStatusModel(StrictBaseModel):
    code: int
    timestamp: datetime
    version: str


class VideoResponseModel(StrictBaseModel):
    content_info: VideoResponseContentInfoModel
    cookie_info: VideoResponseCookieInfoModel
    status: VideoStatusModel
