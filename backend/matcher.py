"""
The matching queue (SPEC section 7).

This file knows nothing about WebSockets. It only keeps track of:
  - waiting: users looking for a partner, oldest first (FIFO)
  - pairs:   who is chatting with whom (stored in BOTH directions)

main.py calls these methods and then sends the right events to the browsers.
Keeping it separate means we can unit test the matching rules easily.
"""

import asyncio
import time
from dataclasses import dataclass, field

from models import Filters, Profile


@dataclass
class User:
    id: str
    profile: Profile
    filters: Filters
    joined_at: float = field(default_factory=time.time)
    # Who they chatted with last time, so "Next" doesn't re-pair them instantly.
    last_partner_id: str | None = None


def is_compatible(a: User, b: User) -> bool:
    """True only if A and B accept each other (filters are checked BOTH ways)."""
    if a.id == b.id:
        return False
    # Male only matches Female, Female only matches Male.
    if a.profile.gender == b.profile.gender:
        return False
    # B's age must be in A's range, AND A's age must be in B's range.
    if not (a.filters.age_min <= b.profile.age <= a.filters.age_max):
        return False
    if not (b.filters.age_min <= a.profile.age <= b.filters.age_max):
        return False
    # Empty country list means "any country".
    if a.filters.countries and b.profile.country not in a.filters.countries:
        return False
    if b.filters.countries and a.profile.country not in b.filters.countries:
        return False
    # Don't reconnect the two people who just skipped each other.
    if a.last_partner_id == b.id or b.last_partner_id == a.id:
        return False
    return True


class Matcher:
    def __init__(self):
        self.waiting: list[User] = []
        self.pairs: dict[str, str] = {}
        # Only one coroutine may change the queue at a time, so two people
        # can never grab the same partner.
        self.lock = asyncio.Lock()

    # ---------- helpers (call these only while holding the lock) ----------

    def _remove_from_waiting(self, user_id: str) -> None:
        self.waiting = [u for u in self.waiting if u.id != user_id]

    def _end_pair(self, user_id: str) -> str | None:
        """Break up user's current chat. Returns the partner's id (or None)."""
        partner_id = self.pairs.pop(user_id, None)
        if partner_id is not None:
            self.pairs.pop(partner_id, None)
        return partner_id

    # ---------- public methods used by main.py ----------

    async def join(self, user: User) -> User | None:
        """
        Put a user into matching.
        Returns the partner User if a match was found right away,
        or None if the user was added to the waiting list.
        """
        async with self.lock:
            # Safety: a user can only be in one place at a time.
            self._remove_from_waiting(user.id)
            self._end_pair(user.id)

            for candidate in self.waiting:  # oldest first = fair
                if is_compatible(user, candidate):
                    self.waiting.remove(candidate)
                    self.pairs[user.id] = candidate.id
                    self.pairs[candidate.id] = user.id
                    user.last_partner_id = candidate.id
                    candidate.last_partner_id = user.id
                    return candidate

            user.joined_at = time.time()
            self.waiting.append(user)
            return None

    async def leave(self, user_id: str) -> str | None:
        """
        Remove a user from the queue and from any chat.
        Used for "next", "leave" and disconnects.
        Returns the old partner's id so main.py can tell them "partner_left".
        """
        async with self.lock:
            self._remove_from_waiting(user_id)
            return self._end_pair(user_id)

    def partner_of(self, user_id: str) -> str | None:
        return self.pairs.get(user_id)

    def is_waiting(self, user_id: str) -> bool:
        return any(u.id == user_id for u in self.waiting)
