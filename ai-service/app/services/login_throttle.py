"""In-memory brute-force protection for login.

After MAX_FAILURES wrong passwords for a username within WINDOW_SECONDS, that
username is locked for LOCK_SECONDS (the correct password is refused too).
Unknown usernames are tracked the same way, so the lock does not reveal which
accounts exist.

Limits: state lives in this process only (a restart clears it, and several
workers each keep their own), and an attacker can lock a known username out for
a while. Fine for a single-process demo; use a shared store for more.
"""

import time
from collections import OrderedDict

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60
LOCK_SECONDS = 15 * 60
MAX_TRACKED = 10_000

_clock = time.monotonic
_state: "OrderedDict[str, dict]" = OrderedDict()


class LoginLockedError(Exception):
    def __init__(self, retry_after: int):
        super().__init__("Too many failed sign-in attempts.")
        self.retry_after = retry_after


def _key(username: str) -> str:
    return username.strip().lower()


def reset_all() -> None:
    _state.clear()


def check(username: str) -> None:
    """Raise LoginLockedError while the username is locked."""
    entry = _state.get(_key(username))
    if not entry:
        return

    now = _clock()
    if entry["locked_until"] > now:
        raise LoginLockedError(int(entry["locked_until"] - now) + 1)

    if entry["locked_until"] and entry["locked_until"] <= now:
        _state.pop(_key(username), None)  # lock expired


def record_failure(username: str) -> None:
    key = _key(username)
    now = _clock()
    entry = _state.get(key)

    if entry is None or now - entry["first"] > WINDOW_SECONDS:
        entry = {"count": 0, "first": now, "locked_until": 0.0}

    entry["count"] += 1
    if entry["count"] >= MAX_FAILURES:
        entry["locked_until"] = now + LOCK_SECONDS

    _state[key] = entry
    _state.move_to_end(key)

    while len(_state) > MAX_TRACKED:
        _state.popitem(last=False)


def record_success(username: str) -> None:
    _state.pop(_key(username), None)
