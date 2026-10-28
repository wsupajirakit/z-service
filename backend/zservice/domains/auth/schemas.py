from pydantic import BaseModel, Field

# Bounds stop oversized bodies early; PBKDF2 itself is cheap on long input (HMAC hashes
# long keys once), so the cap is about request size, not hashing cost.
USERNAME_MAX = 64
PASSWORD_MAX = 1024


class AuthRequest(BaseModel):
    username: str = Field(max_length=USERNAME_MAX)
    password: str = Field(max_length=PASSWORD_MAX)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(max_length=PASSWORD_MAX)
    new_password: str = Field(max_length=PASSWORD_MAX)
