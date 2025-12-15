from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    tenant_id: int


def get_current_user() -> CurrentUser:
    # TODO: replace with real auth (JWT/SSO). For now, fixed user.
    return CurrentUser(user_id=3, tenant_id=1)
