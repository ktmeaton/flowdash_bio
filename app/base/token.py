# project/token.py

from itsdangerous import URLSafeTimedSerializer
from decouple import config


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(config("SECRET_KEY"))
    return serializer.dumps(email, salt=config("SECURITY_PASSWORD_SALT"))


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(config("SECRET_KEY"))
    try:
        email = serializer.loads(
            token, salt=config("SECURITY_PASSWORD_SALT"), max_age=expiration
        )
    except Exception:
        return False
    return email