import contextlib
from typing import Literal

from pydantic import field_validator

from fanzadl.constants import USER_AGENT
from fanzadl.functions import hash_signature
from fanzadl.models.video.base import (
    _AuthAwareModel,
    _BaseLibraryItemContentsModel,
    _BaseQualityModel,
    _LibraryIDAwareModel,
)


class VRQualityModel(_BaseQualityModel):
    quality: int | Literal["hq", "uhq"]
    quality_group: str
    quality_short_display_name: str
    part: int
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


class VRDeliveryInfoModel(_AuthAwareModel, _LibraryIDAwareModel):
    download: list[VRQualityModel] | None = None
    stream: list[VRQualityModel]

    @property
    def download_highest(self) -> VRQualityModel:
        if self.download is None:
            err = "No download quality available"
            raise ValueError(err)
        return self.download[-1]

    @property
    def stream_highest(self) -> VRQualityModel:
        return self.stream[-1]

    @field_validator("download", "stream")
    @classmethod
    def sort_members(
        cls, v: list[VRQualityModel] | None
    ) -> list[VRQualityModel] | None:
        if v is None:
            return v
        return sorted(v, key=lambda x: x.quality_order, reverse=False)


class VRRatePatternModel(_AuthAwareModel, _LibraryIDAwareModel):
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


class VRLibraryItemContentsModel(_BaseLibraryItemContentsModel):
    content_type: Literal["vr"]
    vr_rate_pattern: VRRatePatternModel

    @property
    def download_highest(self) -> VRQualityModel:
        dl_list: list[VRQualityModel] = []
        for _, model in self.vr_rate_pattern:
            with contextlib.suppress(ValueError):
                dl_list.append(model.download_highest)
        return max(dl_list, key=lambda x: x.quality_order)
