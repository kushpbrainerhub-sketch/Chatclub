"""
Unit tests for the matching rules (SPEC section 13).
Run from the backend folder with:  pytest
"""

import pytest
from pydantic import ValidationError

from matcher import Matcher, User, is_compatible
from models import Filters, JoinRequest, Profile


def make_user(user_id, gender="male", age=25, country="IN",
              countries=None, age_min=18, age_max=99):
    """Small helper so each test only writes what matters to it."""
    return User(
        id=user_id,
        profile=Profile(username=f"user_{user_id}", age=age, country=country, gender=gender),
        filters=Filters(countries=countries or [], age_min=age_min, age_max=age_max),
    )


# ---------- compatibility rules ----------

def test_male_and_female_with_matching_filters_match():
    assert is_compatible(make_user("a", "male"), make_user("b", "female"))


def test_male_and_male_do_not_match():
    assert not is_compatible(make_user("a", "male"), make_user("b", "male"))


def test_female_and_female_do_not_match():
    assert not is_compatible(make_user("a", "female"), make_user("b", "female"))


def test_age_outside_a_range_does_not_match():
    a = make_user("a", "male", age_min=18, age_max=25)
    b = make_user("b", "female", age=30)
    assert not is_compatible(a, b)


def test_age_outside_b_range_does_not_match_mutual_check():
    # B (age 22) is fine for A, but A (age 40) is too old for B.
    a = make_user("a", "male", age=40, age_min=18, age_max=50)
    b = make_user("b", "female", age=22, age_min=18, age_max=30)
    assert not is_compatible(a, b)
    assert not is_compatible(b, a)


def test_empty_country_filters_match():
    a = make_user("a", "male", country="IN")
    b = make_user("b", "female", country="BR")
    assert is_compatible(a, b)


def test_country_filter_blocks_other_country():
    a = make_user("a", "male", country="IN", countries=["IN"])
    b = make_user("b", "female", country="US")
    assert not is_compatible(a, b)


def test_country_filter_allows_listed_country():
    a = make_user("a", "male", country="IN", countries=["US", "IN"])
    b = make_user("b", "female", country="US")
    assert is_compatible(a, b)


def test_user_is_not_compatible_with_itself():
    a = make_user("a")
    assert not is_compatible(a, a)


# ---------- queue behaviour ----------

@pytest.mark.asyncio
async def test_first_user_waits_second_user_gets_matched():
    matcher = Matcher()
    a, b = make_user("a", "male"), make_user("b", "female")
    assert await matcher.join(a) is None
    assert matcher.is_waiting("a")
    partner = await matcher.join(b)
    assert partner is a
    assert matcher.partner_of("a") == "b"
    assert matcher.partner_of("b") == "a"
    assert matcher.waiting == []


@pytest.mark.asyncio
async def test_oldest_compatible_waiting_user_is_picked_first():
    matcher = Matcher()
    old = make_user("old", "female")
    new = make_user("new", "female")
    await matcher.join(old)
    await matcher.join(new)
    partner = await matcher.join(make_user("m", "male"))
    assert partner is old
    assert matcher.is_waiting("new")


@pytest.mark.asyncio
async def test_incompatible_waiting_users_are_skipped():
    matcher = Matcher()
    await matcher.join(make_user("male1", "male"))
    await matcher.join(make_user("f_far", "female", country="US", countries=["US"]))
    f_ok = make_user("f_ok", "female")
    await matcher.join(f_ok)  # male1 was already waiting, so f_ok matches male1
    assert matcher.partner_of("f_ok") == "male1"
    assert matcher.is_waiting("f_far")


@pytest.mark.asyncio
async def test_user_who_disconnects_is_removed_from_waiting():
    matcher = Matcher()
    await matcher.join(make_user("a", "male"))
    await matcher.leave("a")
    assert not matcher.is_waiting("a")
    # A new female must not be matched with the user who left.
    assert await matcher.join(make_user("b", "female")) is None


@pytest.mark.asyncio
async def test_leave_returns_partner_and_clears_both_sides():
    matcher = Matcher()
    await matcher.join(make_user("a", "male"))
    await matcher.join(make_user("b", "female"))
    assert await matcher.leave("a") == "b"
    assert matcher.partner_of("a") is None
    assert matcher.partner_of("b") is None


@pytest.mark.asyncio
async def test_next_does_not_immediately_repair_same_users():
    matcher = Matcher()
    a, b = make_user("a", "male"), make_user("b", "female")
    await matcher.join(a)
    await matcher.join(b)
    # A presses "Next": the pair ends and both go back to searching.
    await matcher.leave("a")
    assert await matcher.join(a) is None
    assert await matcher.join(b) is None  # not re-paired with A
    # A different female can still match A.
    partner = await matcher.join(make_user("c", "female"))
    assert partner is a


# ---------- validation ----------

def test_age_17_is_rejected():
    with pytest.raises(ValidationError):
        JoinRequest(profile={"username": "kid", "age": 17, "country": "IN", "gender": "male"})


def test_bad_gender_is_rejected():
    with pytest.raises(ValidationError):
        Profile(username="abc", age=20, country="IN", gender="other")


def test_bad_username_is_rejected():
    with pytest.raises(ValidationError):
        Profile(username="<b>", age=20, country="IN", gender="male")


def test_unknown_country_is_rejected():
    with pytest.raises(ValidationError):
        Profile(username="abc", age=20, country="ZZ", gender="male")


def test_filter_min_above_max_is_rejected():
    with pytest.raises(ValidationError):
        Filters(age_min=40, age_max=30)


def test_username_is_trimmed_and_country_uppercased():
    p = Profile(username="  Kush  ", age=22, country="in", gender="male")
    assert p.username == "Kush"
    assert p.country == "IN"
