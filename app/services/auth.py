from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class User:
    username: str
    role: str


ANALYST_CREDENTIALS = {
    "analyst": "letmein",
}

# For constrained contractor access, we allow a known shared tokenized link
# and contractor-specific login code.
CONTRACTOR_TOKENS = {"contractor-demo-token"}
CONTRACTOR_CODES = {"contractor": "contract123"}


class AuthService:
    @staticmethod
    def authenticate_analyst(username: str, password: str) -> Optional[User]:
        expected = ANALYST_CREDENTIALS.get(username)
        if expected and expected == password:
            return User(username=username, role="analyst")
        return None

    @staticmethod
    def authenticate_contractor(username: str, code: str) -> Optional[User]:
        expected = CONTRACTOR_CODES.get(username)
        if expected and expected == code:
            return User(username=username, role="contractor")
        return None

    @staticmethod
    def is_valid_contractor_token(token: Optional[str]) -> bool:
        return bool(token and token in CONTRACTOR_TOKENS)
