from pydantic import Field

from fanzadl.models.strict import StrictBaseModel


class JAVStashSceneModel(StrictBaseModel):
    id: str
    code: str | None = None


class JAVStashQuerySceneModel(StrictBaseModel):
    count: int
    scenes: list[JAVStashSceneModel]


class JAVStashResponseDataModel(StrictBaseModel):
    query_scenes: JAVStashQuerySceneModel = Field(alias="queryScenes")


class JAVStashResponseModel(StrictBaseModel):
    data: JAVStashResponseDataModel
