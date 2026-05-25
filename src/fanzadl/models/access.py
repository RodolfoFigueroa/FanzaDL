from fanzadl.models.strict import StrictBaseModel


class RefreshTokenBodyModel(StrictBaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str


class AccessTokenBodyModel(RefreshTokenBodyModel):
    id_token: str


class AccessTokenDataModel(StrictBaseModel):
    body: AccessTokenBodyModel
    header: dict


class RefreshTokenDataModel(StrictBaseModel):
    body: RefreshTokenBodyModel
    header: dict
