from functools import cached_property
from typing import Literal

from pydantic import ConfigDict, ValidationError, computed_field

from fanzadl.constants import USER_AGENT
from fanzadl.functions import hash_signature
from fanzadl.models.video.base import (
    _BaseLibraryItemContentsModel,
    _BaseQualityModel,
)


class VideoQualityModel(_BaseQualityModel):
    model_config = ConfigDict(frozen=True)

    codec: Literal["h264", "vp9"]
    codec_display_name: Literal["H.264", "VP9"]
    devices: tuple[str, ...]
    height: int
    parts: int
    product_id: str
    quality: int
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


class VideoLibraryItemContentsModel(_BaseLibraryItemContentsModel):
    content_type: Literal["video"]

    @computed_field
    @cached_property
    def device_groups(self) -> list[VideoQualityModel]:
        detail = self.get_detail()

        out: list[VideoQualityModel] = []
        for delivery in detail["delivery_content_info"].values():
            for method_data in delivery.values():
                for device_group in method_data:
                    try:
                        elem = VideoQualityModel.model_validate(device_group)
                        elem._get_authorization = self._get_authorization  # noqa: SLF001
                        elem._get_exploit_id = self._get_exploit_id  # noqa: SLF001
                        elem._mylibrary_id = self.mylibrary_id  # noqa: SLF001
                        out.append(elem)
                    except ValidationError:
                        continue

        return sorted(set(out), key=lambda x: x.quality_order)

    @property
    def download_highest(self) -> VideoQualityModel:
        return self.device_groups[-1]
