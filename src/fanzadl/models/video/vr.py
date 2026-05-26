from typing import Literal

from pydantic import Field

from fanzadl.constants import USER_AGENT
from fanzadl.functions import hash_signature
from fanzadl.models.video.base import (
    _BaseDeliveryInfoModel,
    _BaseLibraryItemContentsModel,
    _BaseQualityModel,
    _BaseRatePatternModel,
)


class VRQualityModel(_BaseQualityModel):
    quality: int | Literal["hq", "uhq"]
    quality_short_display_name: str
    file_size: int | None = None
    url_suffix: Literal["vr"] = "vr"

    def build_signature(self, *, part: int) -> str:
        return hash_signature(
            [
                self.authorization,
                str(self.mylibrary_id),
                self.exploit_id,
                USER_AGENT,
                str(self.quality_group),
                str(part),
            ]
        )


class VRDeliveryInfoModel(_BaseDeliveryInfoModel[VRQualityModel]):
    pass


class VRRatePatternModel(_BaseRatePatternModel[VRQualityModel]):
    android_vr: VRDeliveryInfoModel
    iphone_vr: VRDeliveryInfoModel
    oculusgear_vr: VRDeliveryInfoModel
    oculusgo_vr: VRDeliveryInfoModel
    oculusquest_vr: VRDeliveryInfoModel
    oculusquest2_vr: VRDeliveryInfoModel
    pc_vr: VRDeliveryInfoModel
    pico4_vr: VRDeliveryInfoModel
    psvr: VRDeliveryInfoModel
    psvr2: VRDeliveryInfoModel
    quest3_vr: VRDeliveryInfoModel
    quest3s_vr: VRDeliveryInfoModel
    questpro_vr: VRDeliveryInfoModel
    windowsmr_vr: VRDeliveryInfoModel
    xperia_vr: VRDeliveryInfoModel


class VRLibraryItemContentsModel(_BaseLibraryItemContentsModel[VRQualityModel]):
    content_type: Literal["vr"]
    video_list: VRRatePatternModel = Field(alias="vr_rate_pattern")
