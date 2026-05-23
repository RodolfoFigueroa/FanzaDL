from fanzadl.models.strict import StrictBaseModel


class UserDataModel(StrictBaseModel):
    aud: str
    exp: int
    iat: int
    iss: str
    nonce: None
    user_id: str
