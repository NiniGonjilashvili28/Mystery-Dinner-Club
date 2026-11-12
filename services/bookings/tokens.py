"""Login tokens: a signed note saying "this is user 7", which the browser sends back.

The UI and the services live at different addresses, so a login cookie would not travel
reliably between them. Instead, /login returns a token and the UI sends it in the
Authorization header. It is signed with SECRET_KEY, so it cannot be forged or edited.
"""
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

MAX_AGE_SECONDS = 7 * 24 * 3600   # a login lasts one week


def make_token(secret_key, user_id):
    return URLSafeTimedSerializer(secret_key, salt="login").dumps({"user_id": user_id})


def read_token(secret_key, token):
    """The user id inside a valid token, or None if it is missing, forged or too old."""
    if not token:
        return None
    try:
        data = URLSafeTimedSerializer(secret_key, salt="login").loads(token, max_age=MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("user_id")