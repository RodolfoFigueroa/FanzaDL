from typing import Generic, TypeVar

from fanzadl.models.strict import StrictBaseModel


class RefreshTokenBodyModel(StrictBaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str


class AccessTokenBodyModel(RefreshTokenBodyModel):
    id_token: str


BodyT = TypeVar("BodyT", bound=RefreshTokenBodyModel, default=RefreshTokenBodyModel)


class _BaseTokenDataModel(StrictBaseModel, Generic[BodyT]):
    body: BodyT
    header: dict


class AccessTokenDataModel(_BaseTokenDataModel[AccessTokenBodyModel]):
    pass


class RefreshTokenDataModel(_BaseTokenDataModel[RefreshTokenBodyModel]):
    pass
