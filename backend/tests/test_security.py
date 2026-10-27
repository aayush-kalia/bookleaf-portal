from uuid import uuid4

import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify():
    password = "Strong-Test-Password-123!"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_round_trip():
    user_id = uuid4()

    token = create_access_token(user_id, "author")
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "author"


def test_invalid_token_is_rejected():
    try:
        decode_access_token("not-a-valid-token")
    except jwt.InvalidTokenError:
        pass
    else:
        raise AssertionError("Invalid token should be rejected")