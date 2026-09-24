"""
Pydantic models = the "shape" of the data we accept from the browser.

Pydantic checks types for us, and our validators check the rules from
SPEC section 5. The backend never trusts the frontend, so every "join"
message goes through these models before the user enters the queue.
"""

import re

from pydantic import BaseModel, ValidationError, field_validator, model_validator
from typing import Literal

from countries import COUNTRY_CODES

MIN_AGE = 18
MAX_AGE = 99
MAX_MESSAGE_LENGTH = 1000

# Letters, numbers, underscore, dot and space. 3 to 20 characters.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_. ]{3,20}$")


def check_age(age: int) -> int:
    if not (MIN_AGE <= age <= MAX_AGE):
        raise ValueError(f"Age must be between {MIN_AGE} and {MAX_AGE}")
    return age


def check_country(code: str) -> str:
    code = code.strip().upper()
    if code not in COUNTRY_CODES:
        raise ValueError(f"Unknown country code: {code}")
    return code


class Profile(BaseModel):
    username: str
    age: int
    country: str
    gender: Literal["male", "female"]

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.match(value):
            raise ValueError(
                "Username must be 3-20 characters: letters, numbers, _ . or space"
            )
        return value

    @field_validator("age")
    @classmethod
    def validate_age(cls, value: int) -> int:
        return check_age(value)

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        return check_country(value)


class Filters(BaseModel):
    countries: list[str] = []  # empty list = any country
    age_min: int = MIN_AGE
    age_max: int = MAX_AGE

    @field_validator("countries")
    @classmethod
    def validate_countries(cls, value: list[str]) -> list[str]:
        cleaned = [check_country(code) for code in value]
        return sorted(set(cleaned))  # remove duplicates

    @field_validator("age_min", "age_max")
    @classmethod
    def validate_age_range(cls, value: int) -> int:
        return check_age(value)

    @model_validator(mode="after")
    def min_not_above_max(self):
        if self.age_min > self.age_max:
            raise ValueError("Minimum age cannot be bigger than maximum age")
        return self


class JoinRequest(BaseModel):
    profile: Profile
    filters: Filters = Filters()


def clean_message_text(text) -> str:
    """Return trimmed message text, or raise ValueError if it is not allowed."""
    if not isinstance(text, str):
        raise ValueError("Message must be text")
    text = text.strip()
    if not text:
        raise ValueError("Message cannot be empty")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message is too long (max {MAX_MESSAGE_LENGTH} characters)")
    return text


def friendly_error(error: ValidationError) -> str:
    """Turn Pydantic's long error into one short sentence for the user."""
    first = error.errors()[0]
    if first["type"] == "value_error":
        # Our own ValueError messages are already friendly.
        return first["msg"].removeprefix("Value error, ")
    field = ".".join(str(part) for part in first["loc"])
    return f"{field}: {first['msg']}"
