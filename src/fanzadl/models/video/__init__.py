from typing import Annotated

from pydantic import Field, TypeAdapter

from fanzadl.models.video.unavailable import (
    UnavailableVideoItemContentsModel,
    UnavailableVRItemContentsModel,
)
from fanzadl.models.video.video import VideoLibraryItemContentsModel
from fanzadl.models.video.vr import VRLibraryItemContentsModel

LibraryItemContentsModel = Annotated[
    VideoLibraryItemContentsModel | VRLibraryItemContentsModel,
    Field(discriminator="content_type"),
]
UnavailableLibraryItemContentsModel = Annotated[
    UnavailableVideoItemContentsModel | UnavailableVRItemContentsModel,
    Field(discriminator="content_type"),
]

library_item_adapter = TypeAdapter(LibraryItemContentsModel)

__all__ = [
    "LibraryItemContentsModel",
    "UnavailableLibraryItemContentsModel",
    "VRLibraryItemContentsModel",
    "VideoLibraryItemContentsModel",
    "library_item_adapter",
]
