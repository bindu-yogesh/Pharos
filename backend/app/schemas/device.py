from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(min_length=1, max_length=500)


class DeviceResponse(BaseModel):
    message: str