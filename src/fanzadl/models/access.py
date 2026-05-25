from fanzadl.models.strict import StrictBaseModel


class AccessTokenBodyModel(StrictBaseModel):
    access_token: str
    refresh_token: str
    id_token: str
    token_type: str
    expires_in: int
    scope: str


class AccessTokenDataModel(StrictBaseModel):
    body: AccessTokenBodyModel
    header: dict


class RefreshTokenBodyModel(StrictBaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str


class RefreshTokenDataModel(StrictBaseModel):
    body: RefreshTokenBodyModel
    header: dict
