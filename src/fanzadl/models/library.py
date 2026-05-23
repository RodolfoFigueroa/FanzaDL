from datetime import datetime

from pydantic import Field

from fanzadl.models.strict import StrictBaseModel


class LibraryItemModel(StrictBaseModel):
    contents: dict


class LibraryDataModel(StrictBaseModel):
    content_total: int
    list_: list[LibraryItemModel] = Field(alias="list")
    reserve_notice: list
    page: int
    page_total: int
    all_total: int
    hidden_total: int
    current_time: datetime
