from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator



def validate_bcrypt_password_length(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes")
    return value


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        return validate_bcrypt_password_length(value)

    preferred_language: str = Field(default="en", pattern="^(en|hi|kn)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        return validate_bcrypt_password_length(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    preferred_language: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    preferred_language: str = Field(pattern="^(en|hi|kn)$")

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name must not be blank")
        return value
