from typing import Literal

from pydantic import (
    ConfigDict,
    Field,
)

from fanzadl.constants import USER_AGENT
from fanzadl.functions import hash_signature
from fanzadl.models.video.base import (
    _BaseDeliveryInfoModel,
    _BaseLibraryItemContentsModel,
    _BaseQualityModel,
    _BaseRatePatternModel,
)


class VideoQualityModel(_BaseQualityModel):
    model_config = ConfigDict(frozen=True)

    codec: Literal["h264", "vp9"]
    codec_display_name: Literal["H.264", "VP9"]
    devices: tuple[str, ...]
    height: int
    parts: int
    product_id: str
    quality: int | str
    quality_display_name_en: str
    quality_short_display_name: str
    recommended_viewing_type: str | None
    url_suffix: Literal["2d"] = "2d"
    width: int

    def build_signature(self, *, part: int) -> str:
        return hash_signature(
            [
                USER_AGENT,
                str(part),
                self.authorization,
                self.exploit_id,
                str(self.mylibrary_id),
            ]
        )


class VideoDeliveryInfoModel(_BaseDeliveryInfoModel[VideoQualityModel]):
    pass


class VideoRatePatternModel(_BaseRatePatternModel[VideoQualityModel]):
    amazonfire: VideoDeliveryInfoModel
    amazonfire_4k: VideoDeliveryInfoModel
    amazonfirestick: VideoDeliveryInfoModel
    android: VideoDeliveryInfoModel
    androidtv: VideoDeliveryInfoModel
    appletv: VideoDeliveryInfoModel
    aquos: VideoDeliveryInfoModel
    bravia: VideoDeliveryInfoModel
    chromecast: VideoDeliveryInfoModel
    chromecast_4k: VideoDeliveryInfoModel
    chromecast_hd: VideoDeliveryInfoModel
    html5tv: VideoDeliveryInfoModel
    html5tv_4k: VideoDeliveryInfoModel
    iphone: VideoDeliveryInfoModel
    pc: VideoDeliveryInfoModel
    ps4: VideoDeliveryInfoModel
    ps4_pro: VideoDeliveryInfoModel
    ps5: VideoDeliveryInfoModel
    regza: VideoDeliveryInfoModel
    viera: VideoDeliveryInfoModel
    vita_tv: VideoDeliveryInfoModel = Field(alias="vita-tv")
    vita: VideoDeliveryInfoModel


class VideoLibraryItemContentsModel(_BaseLibraryItemContentsModel[VideoQualityModel]):
    content_type: Literal["video"]
    video_list: VideoRatePatternModel
