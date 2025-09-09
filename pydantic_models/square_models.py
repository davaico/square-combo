from pydantic import BaseModel

class SquareObtainTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: int
    refresh_token: str
    merchant_id: str
    short_lived: bool