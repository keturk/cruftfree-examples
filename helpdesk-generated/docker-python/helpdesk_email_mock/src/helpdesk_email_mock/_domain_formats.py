"""The shared value checks: the domain-scalar formats, the ``Validator`` shape checks and algorithms.

Every text-valued domain scalar (Email, URL, IPAddress, CIDR, IBAN, ...) has a
format here. The schemas' ``Field(pattern=...)`` carries each format's grammar;
the ``_cruftfree_require_<scalar>`` after-validators enforce a format's whole rule
(bounds, grammar and check), and a ``_cruftfree_require_<scalar>_text``
before-validator holds a text input of a non-text type (``UUID``) to its format
before the type converts it. ``Validator.isEmail``/``isUrl``/``isPhone`` call
:func:`_cruftfree_matches_domain_format`. A number or boolean field of a body,
message or struct is held by :func:`require_json_number` /
:func:`require_json_boolean` to the JSON kind it already has, so no text is read
into it; only a route parameter, which arrives as text, is.

Every other shape check (``Validator.isHex``, ``isUuid``, ``isStrongPassword``,
...) and the ``String`` predicates ``isAlpha``/``isAlphanumeric``/``isNumeric``
call :func:`_cruftfree_matches_validator_format`; ``Validator.isCreditCard``,
``isDate``, ``isJson`` and ``isEmpty`` run the shared check algorithms below.

Every bound, pattern and check is rendered from the one shared definition, so
a value is accepted or refused exactly as seed analysis and every other target
accept or refuse it.
"""

from __future__ import annotations

import base64
import datetime
import json
import math
import re
from collections.abc import Callable
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer

# The shared domain-format checks.
_MOD97_MODULUS = 97
_MOD97_VALID_REMAINDER = 1
_MOD97_CHECK_PREFIX_LENGTH = 4
_BASE36 = 36
_SINGLE_DIGIT_LIMIT = 10
_ONE_DIGIT_SCALE = 10
_TWO_DIGIT_SCALE = 100

_IPV4_BITS = 32
_IPV4_OCTET_BITS = 8
_IPV6_BITS = 128
_IPV6_GROUP_BITS = 16
_IPV6_GROUPS = 8
_IPV6_GROUP_MASK = 0xFFFF
_HEX_BASE = 16

#: RFC 5321: the local part of a mailbox has 1-64 characters; every target's email check reads these.
EMAIL_LOCAL_PART_MIN_LENGTH = 1
EMAIL_LOCAL_PART_MAX_LENGTH = 64

#: RFC 1035: a DNS label has at most 63 characters; every target's domain-name check reads these.
DNS_LABEL_MAX_LENGTH = 63

#: The top-level label of a domain name has 2-63 letters.
TOP_LEVEL_LABEL_MIN_LENGTH = 2
TOP_LEVEL_LABEL_MAX_LENGTH = 63

#: What separates a URL's scheme from its host, and what ends the host: a port, a path,
#: a query or a fragment. Every target's URL host check reads these.
URL_SCHEME_SEPARATOR = "://"
URL_HOST_ENDS = ":/?#"


def iso7064_mod97_10_valid(text: str) -> bool:
    """True when *text* (upper-case letters and digits) passes ISO 7064 MOD 97-10.

    The first four characters move to the end, every letter becomes its two-digit
    number (``A`` = 10 ... ``Z`` = 35), and the resulting integer must leave a
    remainder of 1 when divided by 97. The remainder is folded character by
    character, so the integer is never built.
    """
    rearranged = text[_MOD97_CHECK_PREFIX_LENGTH:] + text[:_MOD97_CHECK_PREFIX_LENGTH]
    remainder = 0
    for character in rearranged:
        if not ("0" <= character <= "9" or "A" <= character <= "Z"):
            return False
        value = int(character, _BASE36)
        scale = _ONE_DIGIT_SCALE if value < _SINGLE_DIGIT_LIMIT else _TWO_DIGIT_SCALE
        remainder = (remainder * scale + value) % _MOD97_MODULUS
    return remainder == _MOD97_VALID_REMAINDER


def _ipv4_address_value(text: str) -> int:
    """The 32-bit value of a dotted-quad IPv4 address."""
    value = 0
    for octet in text.split("."):
        value = (value << _IPV4_OCTET_BITS) | int(octet)
    return value


def _ipv6_address_value(text: str) -> int:
    """The 128-bit value of an RFC 4291 IPv6 address, ``::`` and an embedded IPv4 tail included."""
    if "." in text:
        head, _, tail = text.rpartition(":")
        tail_value = _ipv4_address_value(tail)
        text = (
            head
            + ":"
            + format(tail_value >> _IPV6_GROUP_BITS, "x")
            + ":"
            + format(tail_value & _IPV6_GROUP_MASK, "x")
        )
    if "::" in text:
        left, right = text.split("::")
        left_groups = left.split(":") if left else []
        right_groups = right.split(":") if right else []
        zeros = ["0"] * (_IPV6_GROUPS - len(left_groups) - len(right_groups))
        groups = left_groups + zeros + right_groups
    else:
        groups = text.split(":")
    value = 0
    for group in groups:
        value = (value << _IPV6_GROUP_BITS) | int(group, _HEX_BASE)
    return value


def network_prefix_valid(text: str) -> bool:
    """True when the CIDR *text* (``address/prefix``) sets no address bit after its prefix.

    ``192.168.1.0/24`` names a network; ``192.168.1.1/24`` names a host inside
    one and is refused, as a ``cidr`` column refuses it.
    """
    address, _, prefix_text = text.rpartition("/")
    if ":" in address:
        bits, value = _IPV6_BITS, _ipv6_address_value(address)
    else:
        bits, value = _IPV4_BITS, _ipv4_address_value(address)
    host_bits = bits - int(prefix_text)
    return value & ((1 << host_bits) - 1) == 0


def domain_name_labels_valid(name: str) -> bool:
    """True when every dot-separated label of the domain *name* has at most 63 characters
    and the last (top-level) label has 2-63.

    The grammar reads each label's shape and this check counts it, so the
    grammar's repetitions need no count that could overlap what follows them.
    """
    labels = name.split(".")
    top_level = labels[-1]
    return (
        all(len(label) <= DNS_LABEL_MAX_LENGTH for label in labels)
        and TOP_LEVEL_LABEL_MIN_LENGTH <= len(top_level) <= TOP_LEVEL_LABEL_MAX_LENGTH
    )


def email_address_valid(text: str) -> bool:
    """True when the email *text*'s local part (before its last ``@``) has 1-64 characters
    and the domain name after it passes :func:`domain_name_labels_valid`.

    RFC 5321 bounds a mailbox's local part at 64 characters. A text with no
    ``@`` has no local part and is refused.
    """
    local_part, _, domain_name = text.rpartition("@")
    return EMAIL_LOCAL_PART_MIN_LENGTH <= len(
        local_part
    ) <= EMAIL_LOCAL_PART_MAX_LENGTH and domain_name_labels_valid(domain_name)


def _is_ascii_letters(text: str) -> bool:
    """True when *text* is one or more ASCII letters."""
    return text != "" and all(
        "A" <= character <= "Z" or "a" <= character <= "z" for character in text
    )


def url_host_valid(text: str) -> bool:
    """True when the host of the URL *text* is an IP address or passes :func:`domain_name_labels_valid`.

    The host runs from after ``://`` to the first ``:``, ``/``, ``?`` or ``#``,
    or the end. A host starting with ``[`` is an IPv6 address, and a host whose
    last label is not letters is an IPv4 address: the grammar has read both
    whole, so they pass.
    """
    _, _, rest = text.partition(URL_SCHEME_SEPARATOR)
    ends = [
        index
        for index in (rest.find(character) for character in URL_HOST_ENDS)
        if index >= 0
    ]
    host = rest[: min(ends, default=len(rest))]
    if host.startswith("[") or not _is_ascii_letters(host.rpartition(".")[2]):
        return True
    return domain_name_labels_valid(host)


# The shared ``Validator`` check algorithms.
#: The characters a card number may be grouped by; removed before the digits are read.
CARD_SEPARATOR_PATTERN = "[ \\-]"
#: A card number, once its separators are removed: 12-19 ASCII digits.
CARD_DIGITS_PATTERN = "[0-9]{12,19}"
LUHN_MODULUS = 10
LUHN_DOUBLED_LIMIT = 9

#: ``yyyy-MM-dd``, optionally followed by ``T`` or a space, ``HH:mm``, optional
#: ``:ss`` with an optional 1-9 digit fraction, and an optional ``Z`` or
#: ``+HH:mm``/``+HHmm`` offset. Groups: year, month, day, hour, minute, second.
ISO_DATE_PATTERN = (
    "([0-9]{4})-([0-9]{2})-([0-9]{2})"
    "(?:[T ]([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\\.[0-9]{1,9})?)?"
    "(?:Z|[+\\-](?:[01][0-9]|2[0-3]):?[0-5][0-9])?)?"
)
#: ``d/M/yyyy`` or ``M/d/yyyy``: valid when either reading is a calendar date.
SLASH_DATE_PATTERN = "([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})"
#: ``d-M-yyyy``.
DASH_DATE_PATTERN = "([0-9]{1,2})-([0-9]{1,2})-([0-9]{4})"

MIN_YEAR = 1
MAX_HOUR = 23
MAX_MINUTE = 59
MAX_SECOND = 59
#: Days per month, January first, in a common year; February gains one in a leap year.
DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_FEBRUARY = 2
_LEAP_DIVISOR = 4
_CENTURY = 100
_LEAP_CENTURY = 400

_CARD_SEPARATORS = re.compile("[ \\-]")
_CARD_DIGITS = re.compile("\\A(?:[0-9]{12,19})\\Z")
_ISO_DATE = re.compile(
    "\\A(?:([0-9]{4})-([0-9]{2})-([0-9]{2})(?:[ T]([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\\.[0-9]{1,9})?)?(?:Z|[+\\-](?:[0-1][0-9]|2[0-3]):?[0-5][0-9])?)?)\\Z"
)
_SLASH_DATE = re.compile("\\A(?:([0-9]{1,2})/([0-9]{1,2})/([0-9]{4}))\\Z")
_DASH_DATE = re.compile("\\A(?:([0-9]{1,2})-([0-9]{1,2})-([0-9]{4}))\\Z")


def card_number_valid(value: object) -> bool:
    """True when *value* is a card number passing the Luhn check.

    ASCII spaces and hyphens are removed; what remains must be 12-19 ASCII
    digits whose Luhn sum is a multiple of 10. The card brand is not checked.
    """
    if not isinstance(value, str):
        return False
    digits = _CARD_SEPARATORS.sub("", value)
    if _CARD_DIGITS.fullmatch(digits) is None:
        return False
    total = 0
    for position, character in enumerate(reversed(digits)):
        digit = ord(character) - ord("0")
        if position % 2 == 1:
            digit *= 2
            if digit > LUHN_DOUBLED_LIMIT:
                digit -= LUHN_DOUBLED_LIMIT
        total += digit
    return total % LUHN_MODULUS == 0


def _is_leap_year(year: int) -> bool:
    return year % _LEAP_DIVISOR == 0 and (
        year % _CENTURY != 0 or year % _LEAP_CENTURY == 0
    )


def _calendar_date_valid(year: int, month: int, day: int) -> bool:
    """True when *year*-*month*-*day* is a day of the Gregorian calendar, from year 1."""
    if year < MIN_YEAR or not 1 <= month <= len(DAYS_IN_MONTH) or day < 1:
        return False
    days = DAYS_IN_MONTH[month - 1] + (
        1 if month == _FEBRUARY and _is_leap_year(year) else 0
    )
    return day <= days


def _iso_date_valid(match: re.Match[str]) -> bool:
    year, month, day, hour, minute, second = match.groups()
    if not _calendar_date_valid(int(year), int(month), int(day)):
        return False
    if hour is None:
        return True
    return (
        int(hour) <= MAX_HOUR
        and int(minute) <= MAX_MINUTE
        and (second is None or int(second) <= MAX_SECOND)
    )


def date_text_valid(value: object) -> bool:
    """True when *value* is a date written in one of the accepted forms.

    The forms: ISO ``yyyy-MM-dd`` with an optional time (``T`` or a space,
    ``HH:mm``, optional ``:ss`` and fraction, optional ``Z`` or offset);
    ``d/M/yyyy`` or ``M/d/yyyy``; ``d-M-yyyy``. The whole value is the date --
    nothing around it -- and every component is checked against the calendar
    (no 31 April, 29 February only in a leap year, hours to 23, minutes and
    seconds to 59).
    """
    if not isinstance(value, str):
        return False
    iso = _ISO_DATE.fullmatch(value)
    if iso is not None:
        return _iso_date_valid(iso)
    slash = _SLASH_DATE.fullmatch(value)
    if slash is not None:
        first, second, year = (int(part) for part in slash.groups())
        return _calendar_date_valid(year, second, first) or _calendar_date_valid(
            year, first, second
        )
    dash = _DASH_DATE.fullmatch(value)
    if dash is not None:
        day, month, year = (int(part) for part in dash.groups())
        return _calendar_date_valid(year, month, day)
    return False


def _refuse_non_json_constant(name: str) -> object:
    """``json.loads`` hook: ``NaN``, ``Infinity`` and ``-Infinity`` are not JSON (RFC 8259)."""
    raise ValueError(f"{name} is not a JSON value")


def json_text_valid(value: object) -> bool:
    """True when *value* is one RFC 8259 JSON text: any value, surrounded only by JSON whitespace."""
    if not isinstance(value, str):
        return False
    try:
        json.loads(value, parse_constant=_refuse_non_json_constant)
    except (ValueError, RecursionError):
        return False
    return True


def value_is_empty(value: object) -> bool:
    """True when *value* is absent, or a text, byte string, list, set or map with nothing in it.

    A number or a boolean is never empty.
    """
    if value is None:
        return True
    if isinstance(value, (str, bytes, list, tuple, set, frozenset, dict)):
        return len(value) == 0
    return False


# The shared ``Duration`` wire form: its ISO-8601 grammar and canonical text.
#: After the digits of the seconds: an optional fraction and ``S``.
_SECONDS_ON = "(?:\\.[0-9]+)?S"
#: After the digits of the minutes: ``M``, then optionally the seconds.
_MINUTES_ON = "M(?:[0-9]+" + _SECONDS_ON + ")?"
#: After the digits of the hours: ``H``, then optionally the minutes or the seconds.
_HOURS_ON = "H(?:[0-9]+(?:" + _MINUTES_ON + "|" + _SECONDS_ON + "))?"
#: ``T`` and at least one of hours, minutes and seconds, in that order.
_TIME_PART = "T[0-9]+(?:" + _HOURS_ON + "|" + _MINUTES_ON + "|" + _SECONDS_ON + ")"
#: Weeks, days, or weeks then days.
_DATE_PART = "[0-9]+(?:W(?:[0-9]+D)?|D)"

#: The whole text a ``Duration`` is read from, in the regex pattern language of
#: ``cruftfree_common.builtins.regex_pattern`` (``domain_formats`` reads it at import):
#: an optional ``-``, ``P``, then the date part, the date part and the time part, or
#: the time part. Each unit is written at most once, in order, and the digits of one
#: are read before the letter naming it, so no repetition and what follows it can
#: both start with one character.
ISO_DURATION_PATTERN: str = (
    "-?P(?:" + _DATE_PART + "(?:" + _TIME_PART + ")?|" + _TIME_PART + ")"
)

#: What a text outside :data:`ISO_DURATION_PATTERN` is refused with, on every target.
INVALID_ISO_DURATION: str = (
    "A Duration must be an ISO-8601 duration of weeks, days, hours, minutes and "
    "seconds, such as 'PT1H30M' or 'P2DT4H'."
)

_ISO_DURATION = re.compile(
    "\\A(?:-?P(?:[0-9]+(?:W(?:[0-9]+D)?|D)(?:T[0-9]+(?:H(?:[0-9]+(?:M(?:[0-9]+(?:\\.[0-9]+)?S)?|(?:\\.[0-9]+)?S))?|M(?:[0-9]+(?:\\.[0-9]+)?S)?|(?:\\.[0-9]+)?S))?|T[0-9]+(?:H(?:[0-9]+(?:M(?:[0-9]+(?:\\.[0-9]+)?S)?|(?:\\.[0-9]+)?S))?|M(?:[0-9]+(?:\\.[0-9]+)?S)?|(?:\\.[0-9]+)?S)))\\Z"
)
_MICROS_PER_SECOND = 1_000_000
_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60
_HOURS_PER_DAY = 24
_DAYS_PER_WEEK = 7
_FRACTION_DIGITS = 6
#: The seconds each unit letter but ``S`` counts; ``M`` is minutes, the grammar
#: having no months.
_UNIT_SECONDS = {
    "W": _DAYS_PER_WEEK * _HOURS_PER_DAY * _MINUTES_PER_HOUR * _SECONDS_PER_MINUTE,
    "D": _HOURS_PER_DAY * _MINUTES_PER_HOUR * _SECONDS_PER_MINUTE,
    "H": _MINUTES_PER_HOUR * _SECONDS_PER_MINUTE,
    "M": _SECONDS_PER_MINUTE,
}
_NUMBER_CHARACTERS = frozenset("0123456789.")


def iso_duration_micros(text: object) -> int:
    """The microseconds the ISO-8601 duration *text* spells.

    The whole text matches :data:`ISO_DURATION_PATTERN` first, so each number is
    ASCII digits (the seconds' with an optional fraction) followed by the letter of
    its unit, every unit at most once.

    Raises:
        ValueError: *text* is not a string holding such a duration
            (:data:`INVALID_ISO_DURATION`).
    """
    if not isinstance(text, str) or _ISO_DURATION.fullmatch(text) is None:
        raise ValueError(INVALID_ISO_DURATION)
    seconds = 0
    fraction_micros = 0
    number = ""
    for character in text:
        if character in _NUMBER_CHARACTERS:
            number += character
        elif character in _UNIT_SECONDS:
            seconds += int(number) * _UNIT_SECONDS[character]
            number = ""
        elif character == "S":
            whole, _, fraction = number.partition(".")
            seconds += int(whole)
            fraction_micros = int(
                fraction[:_FRACTION_DIGITS].ljust(_FRACTION_DIGITS, "0")
            )
            number = ""
    micros = seconds * _MICROS_PER_SECOND + fraction_micros
    return -micros if text.startswith("-") else micros


def iso_duration_from_micros(micros: int) -> str:
    """*micros* microseconds written canonically (``[-]P[nD][T[nH][nM][n[.f]S]]``, ``PT0S`` for zero)."""
    sign = "-" if micros < 0 else ""
    seconds_total, fraction = divmod(abs(micros), _MICROS_PER_SECOND)
    minutes_total, seconds = divmod(seconds_total, _SECONDS_PER_MINUTE)
    hours_total, minutes = divmod(minutes_total, _MINUTES_PER_HOUR)
    days, hours = divmod(hours_total, _HOURS_PER_DAY)
    second_text = (
        f"{seconds}.{fraction:0{_FRACTION_DIGITS}d}".rstrip("0")
        if fraction
        else str(seconds)
    )
    date_part = f"{days}D" if days else ""
    time_part = "".join(
        f"{amount}{unit}"
        for amount, unit in ((str(hours), "H"), (str(minutes), "M"), (second_text, "S"))
        if amount != "0"
    )
    if not date_part and not time_part:
        return "PT0S"
    return f"{sign}P{date_part}{'T' + time_part if time_part else ''}"


def parse_iso_duration(text: object) -> datetime.timedelta:
    """The duration the ISO-8601 *text* spells.

    Raises:
        ValueError: *text* is not a string in :data:`ISO_DURATION_PATTERN`.
    """
    return datetime.timedelta(microseconds=iso_duration_micros(text))


def format_iso_duration(value: datetime.timedelta) -> str:
    """*value* as its canonical ISO-8601 duration text."""
    return iso_duration_from_micros(
        (
            value.days * _HOURS_PER_DAY * _MINUTES_PER_HOUR * _SECONDS_PER_MINUTE
            + value.seconds
        )
        * _MICROS_PER_SECOND
        + value.microseconds
    )


# The JSON kind a body number or boolean already has: never read from text.
def require_json_number(value: object) -> object:
    """*value* when it is a finite number; text, a boolean and a non-finite float are refused."""
    if isinstance(value, (str, bytes, bytearray, bool)):
        raise ValueError(f"must be a JSON number, not {type(value).__name__}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("must be a finite JSON number")
    return value


def require_json_boolean(value: object) -> object:
    """*value* when it is a boolean; text and numbers are refused."""
    if not isinstance(value, bool):
        raise ValueError(f"must be a JSON boolean, not {type(value).__name__}")
    return value


def _cruftfree_require_duration_text(value: object) -> object:
    """A Pydantic before-validator reading a ``Duration`` from exactly its ISO-8601 wire text.

    A ``timedelta`` (a value the service built) passes unchanged; any other
    value -- a bare number, ``P1Y``, ``1:30:00`` -- is refused, as on every target.
    """
    if isinstance(value, datetime.timedelta):
        return value
    return parse_iso_duration(value)


def _cruftfree_duration_text(value: datetime.timedelta) -> str:
    """A ``Duration`` as its canonical ISO-8601 wire text, the text every target writes."""
    return format_iso_duration(value)


def _cruftfree_read_json_bytes(value: object) -> object:
    """A Pydantic before-validator reading a ``Bytes`` value from its JSON form.

    The JSON form is RFC 4648 standard base64 text, padded (the empty text is the
    empty value); any other text or kind is refused, as on every target. A
    ``bytes`` value the service built passes unchanged.
    """
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if value == "":
        return b""
    if not _cruftfree_matches_validator_format("isBase64", value):
        raise ValueError("must be RFC 4648 standard base64 text, padded")
    return base64.b64decode(str(value), validate=True)


def _cruftfree_json_bytes_text(value: bytes) -> str:
    """A ``Bytes`` value as its JSON form: RFC 4648 standard base64 text, padded."""
    return base64.b64encode(value).decode("ascii")


#: A ``bytes`` annotation read from and written as the JSON form of a ``Bytes`` value, for a
#: model that names its types as annotations (an extern service's DTOs and client results).
CruftFreeJsonBytes = Annotated[
    bytes,
    BeforeValidator(_cruftfree_read_json_bytes),
    PlainSerializer(_cruftfree_json_bytes_text, when_used="json"),
]

#: Per format: the fewest and most characters, the grammar the whole value
#: matches, the check the value passes (``None`` when it has none), and the
#: format in words.
_CRUFTFREE_DOMAIN_FORMATS: dict[
    str, tuple[int, int, re.Pattern[str], Callable[[str], bool] | None, str]
] = {
    "Email": (
        1,
        254,
        re.compile(
            "\\A(?:[!#-'*-+\\-/-9=?A-Z\\^-\\~]+(?:\\.[!#-'*-+\\-/-9=?A-Z\\^-\\~]+)*@(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+))\\Z"
        ),
        email_address_valid,
        "local@domain: an RFC 5322 dot-atom local part of at most 64 characters and a domain name of labels of at most 63 characters ending in an alphabetic top-level label of 2-63 letters, at most 254 characters in all",
    ),
    "URL": (
        1,
        8192,
        re.compile(
            "\\A(?:[Hh][Tt][Tt][Pp][Ss]?://(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3}|\\[(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1}|:):(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,2}|:):(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,3}|:):(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,4}|:):(?:[0-9A-Fa-f]{1,4}:){1}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,5}|:):(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,6}|:):[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){1,7}|:):)\\])(?::[0-9]{1,5})?(?:[#/?][!-\\~]*)?)\\Z"
        ),
        url_host_valid,
        "an absolute http or https URL whose host is a domain name, an IPv4 address or a bracketed IPv6 address, with no credentials and no whitespace or non-ASCII characters; a domain-name host has labels of at most 63 characters and a top-level label of 2-63 letters",
    ),
    "Phone": (
        2,
        16,
        re.compile("\\A(?:\\+?[1-9][0-9]{1,14})\\Z"),
        None,
        "an E.164 number: an optional '+', then 2-15 digits not starting with 0",
    ),
    "PostalCode": (
        3,
        10,
        re.compile(
            "\\A(?:(?:[A-Za-z][ \\-]?)*[0-9][0-9A-Za-z]*(?:[ \\-][0-9A-Za-z]+)*)\\Z"
        ),
        None,
        "3-10 characters: groups of letters and digits separated by single spaces or hyphens, with at least one digit",
    ),
    "IBAN": (
        15,
        33,
        re.compile(
            "\\A(?:NO[0-9]{2}[0-9A-Z]{11}|BE[0-9]{2}[0-9A-Z]{12}|(?:DK|FI|FK|FO|GL|NL|SD)[0-9]{2}[0-9A-Z]{14}|(?:MK|SI)[0-9]{2}[0-9A-Z]{15}|(?:AT|BA|EE|KZ|LT|LU|MN|XK)[0-9]{2}[0-9A-Z]{16}|(?:CH|HR|LI|LV)[0-9]{2}[0-9A-Z]{17}|(?:BG|BH|CR|DE|GB|GE|IE|ME|RS|VA)[0-9]{2}[0-9A-Z]{18}|(?:AE|GI|IL|IQ|OM|SO|TL)[0-9]{2}[0-9A-Z]{19}|(?:AD|CZ|ES|MD|PK|RO|SA|SE|SK|TN|VG)[0-9]{2}[0-9A-Z]{20}|(?:LY|PT|ST)[0-9]{2}[0-9A-Z]{21}|(?:IS|TR)[0-9]{2}[0-9A-Z]{22}|(?:BI|DJ|FR|GR|IT|MC|MR|SM)[0-9]{2}[0-9A-Z]{23}|(?:AL|AZ|BY|CY|DO|GT|HN|HU|LB|NI|PL|SV)[0-9]{2}[0-9A-Z]{24}|(?:BR|EG|PS|QA|UA)[0-9]{2}[0-9A-Z]{25}|(?:JO|KW|MU|YE)[0-9]{2}[0-9A-Z]{26}|(?:MT|SC)[0-9]{2}[0-9A-Z]{27}|LC[0-9]{2}[0-9A-Z]{28}|RU[0-9]{2}[0-9A-Z]{29})\\Z"
        ),
        iso7064_mod97_10_valid,
        "an IBAN in electronic format: a registered country code, two check digits and the country's BBAN length of upper-case letters and digits, passing the ISO 7064 MOD 97-10 check",
    ),
    "UUID": (
        36,
        36,
        re.compile(
            "\\A(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\\Z"
        ),
        None,
        "a UUID in 8-4-4-4-12 form: 32 hex digits of either case in five hyphen-separated groups",
    ),
    "IPAddress": (
        2,
        45,
        re.compile(
            "\\A(?:(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3}|(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1}|:):(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,2}|:):(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,3}|:):(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,4}|:):(?:[0-9A-Fa-f]{1,4}:){1}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,5}|:):(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,6}|:):[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){1,7}|:):)\\Z"
        ),
        None,
        "an IPv4 address (four decimal octets of 0-255, no leading zeros) or an IPv6 address in RFC 4291 text form, with an optional embedded IPv4 tail and no zone",
    ),
    "CIDR": (
        3,
        43,
        re.compile(
            "\\A(?:(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3}/(?:3[0-2]|[1-2][0-9]|[0-9])|(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1}|:):(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,2}|:):(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,3}|:):(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,4}|:):(?:[0-9A-Fa-f]{1,4}:){1}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,5}|:):(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,6}|:):[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){1,7}|:):)/(?:12[0-8]|1[0-1][0-9]|[1-9][0-9]|[0-9]))\\Z"
        ),
        network_prefix_valid,
        "a network: an IPv4 address and a /0-32 prefix, or an IPv6 address and a /0-128 prefix, at most 43 characters, with no address bit set after the prefix",
    ),
    "MAC": (
        17,
        17,
        re.compile(
            "\\A(?:[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}|[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5})\\Z"
        ),
        None,
        "a MAC address: six pairs of hex digits separated throughout by ':' or throughout by '-'",
    ),
    "Slug": (
        1,
        8192,
        re.compile("\\A(?:[0-9a-z]+(?:-[0-9a-z]+)*)\\Z"),
        None,
        "one or more groups of lower-case ASCII letters and digits joined by single hyphens",
    ),
    "Color": (
        7,
        7,
        re.compile("\\A(?:#[0-9A-Fa-f]{6})\\Z"),
        None,
        "a colour as '#' and six hex digits of either case (#RRGGBB)",
    ),
    "CountryCode": (
        2,
        2,
        re.compile(
            "\\A(?:A[D-GIL-MOQ-UW-XZ]|B[A-BD-JL-OQ-TV-WY-Z]|C[AC-DF-IK-ORU-Z]|D[EJ-KMOZ]|E[CEG-HR-T]|F[I-KMOR]|G[A-BD-IL-NP-UWY]|H[KM-NRT-U]|I[D-EL-OQ-T]|J[EMO-P]|K[EG-IM-NPRWY-Z]|L[A-CIKR-VY]|M[AC-HK-Z]|N[ACE-GILO-PRUZ]|OM|P[AE-HK-NR-TWY]|QA|R[EOSUW]|S[A-EG-OR-TVX-Z]|T[C-DF-HJ-ORTV-WZ]|U[AGMSY-Z]|V[ACEGINU]|W[FS]|Y[ET]|Z[AMW])\\Z"
        ),
        None,
        "an officially assigned ISO 3166-1 alpha-2 country code in upper case",
    ),
    "LanguageCode": (
        2,
        2,
        re.compile("\\A(?:[a-z]{2})\\Z"),
        None,
        "an ISO 639-1 language code: two lower-case ASCII letters",
    ),
    "CurrencyCode": (
        3,
        3,
        re.compile("\\A(?:[A-Z]{3})\\Z"),
        None,
        "an ISO 4217 currency code: three upper-case ASCII letters",
    ),
    "CreditCard": (
        13,
        19,
        re.compile("\\A(?:[0-9]{13,19})\\Z"),
        card_number_valid,
        "a card number: 13-19 ASCII digits with no separators, passing the Luhn check",
    ),
}


def _cruftfree_matches_domain_format(scalar: str, value: object) -> bool:
    """Whether *value* is a valid *scalar*: within its bounds, matching its grammar, passing its check.

    The length bound is checked before the pattern, so the pattern only ever
    reads a bounded value.
    """
    min_length, max_length, pattern, check, _summary = _CRUFTFREE_DOMAIN_FORMATS[scalar]
    if not isinstance(value, str) or not min_length <= len(value) <= max_length:
        return False
    if pattern.fullmatch(value) is None:
        return False
    return check is None or check(value)


def _cruftfree_domain_format_validator(scalar: str) -> Callable[[str], str]:
    """A Pydantic after-validator refusing any text that is not a valid *scalar*."""
    summary = _CRUFTFREE_DOMAIN_FORMATS[scalar][4]

    def validate(value: str) -> str:
        if not _cruftfree_matches_domain_format(scalar, value):
            raise ValueError(f"must be {summary}")
        return value

    return validate


def _cruftfree_domain_format_text_validator(scalar: str) -> Callable[[object], object]:
    """A Pydantic before-validator holding a text input to *scalar*'s format.

    A value that is not a text (an instance of the field's own type) passes to
    the type's validation unchanged.
    """
    summary = _CRUFTFREE_DOMAIN_FORMATS[scalar][4]

    def validate(value: object) -> object:
        if isinstance(value, str) and not _cruftfree_matches_domain_format(
            scalar, value
        ):
            raise ValueError(f"must be {summary}")
        return value

    return validate


_cruftfree_require_email = _cruftfree_domain_format_validator("Email")
_cruftfree_require_url = _cruftfree_domain_format_validator("URL")
_cruftfree_require_phone = _cruftfree_domain_format_validator("Phone")
_cruftfree_require_postal_code = _cruftfree_domain_format_validator("PostalCode")
_cruftfree_require_iban = _cruftfree_domain_format_validator("IBAN")
_cruftfree_require_ip_address = _cruftfree_domain_format_validator("IPAddress")
_cruftfree_require_cidr = _cruftfree_domain_format_validator("CIDR")
_cruftfree_require_mac = _cruftfree_domain_format_validator("MAC")
_cruftfree_require_slug = _cruftfree_domain_format_validator("Slug")
_cruftfree_require_color = _cruftfree_domain_format_validator("Color")
_cruftfree_require_country_code = _cruftfree_domain_format_validator("CountryCode")
_cruftfree_require_language_code = _cruftfree_domain_format_validator("LanguageCode")
_cruftfree_require_currency_code = _cruftfree_domain_format_validator("CurrencyCode")
_cruftfree_require_credit_card = _cruftfree_domain_format_validator("CreditCard")
_cruftfree_require_uuid_text = _cruftfree_domain_format_text_validator("UUID")


#: Per ``Validator`` check: the fewest and most characters (``None``: the grammar
#: bounds it), the grammar the whole value matches (``None``: none), the check
#: the value passes after it (``None``: none), and the patterns that must each
#: occur somewhere in the value.
_CRUFTFREE_VALIDATOR_FORMATS: dict[
    str,
    tuple[
        int,
        int | None,
        re.Pattern[str] | None,
        Callable[[str], bool] | None,
        tuple[re.Pattern[str], ...],
    ],
] = {
    "isUuid": (
        0,
        None,
        re.compile(
            "\\A(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\\Z"
        ),
        None,
        (),
    ),
    "isMacAddress": (
        0,
        None,
        re.compile(
            "\\A(?:[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}|[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5})\\Z"
        ),
        None,
        (),
    ),
    "isIpv4": (
        0,
        None,
        re.compile(
            "\\A(?:(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})\\Z"
        ),
        None,
        (),
    ),
    "isIpv6": (
        0,
        45,
        re.compile(
            "\\A(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1}|:):(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,2}|:):(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,3}|:):(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,4}|:):(?:[0-9A-Fa-f]{1,4}:){1}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,5}|:):(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,6}|:):[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){1,7}|:):)\\Z"
        ),
        None,
        (),
    ),
    "isIpAddress": (
        0,
        45,
        re.compile(
            "\\A(?:(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3}|(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1}|:):(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,2}|:):(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,3}|:):(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,4}|:):(?:[0-9A-Fa-f]{1,4}:){1}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,5}|:):(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)(?:\\.(?:0|1(?:[0-9][0-9]?)?|2(?:[0-4][0-9]?|5[0-5]?|[6-9])?|[3-9][0-9]?)){3})|(?:(?:[0-9A-Fa-f]{1,4}:){1,6}|:):[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){1,7}|:):)\\Z"
        ),
        None,
        (),
    ),
    "isBase64": (
        0,
        None,
        re.compile(
            "\\A(?:(?:[+/-9A-Za-z]{4})+|[+/-9A-Za-z]{3}(?:[+/-9A-Za-z]{4})*=|[+/-9A-Za-z]{2}(?:[+/-9A-Za-z]{4})*==)\\Z"
        ),
        None,
        (),
    ),
    "isHex": (0, None, re.compile("\\A(?:[0-9A-Fa-f]+)\\Z"), None, ()),
    "isAlpha": (0, None, re.compile("\\A(?:[A-Za-z]+)\\Z"), None, ()),
    "isAlphanumeric": (0, None, re.compile("\\A(?:[0-9A-Za-z]+)\\Z"), None, ()),
    "isNumeric": (0, None, re.compile("\\A(?:[0-9]+)\\Z"), None, ()),
    "isInteger": (0, None, re.compile("\\A(?:-?[0-9]+)\\Z"), None, ()),
    "isFloat": (0, None, re.compile("\\A(?:-?[0-9]+\\.[0-9]+)\\Z"), None, ()),
    "isDomain": (
        0,
        253,
        re.compile(
            "\\A(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+)\\Z"
        ),
        domain_name_labels_valid,
        (),
    ),
    "isHexColor": (
        0,
        None,
        re.compile("\\A(?:#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8}))\\Z"),
        None,
        (),
    ),
    "isSlug": (0, None, re.compile("\\A(?:[0-9a-z]+(?:-[0-9a-z]+)*)\\Z"), None, ()),
    "isCAPostalCode": (
        0,
        None,
        re.compile(
            "\\A(?:[A-CEG-HJ-NPR-TVX-Ya-ceg-hj-npr-tvx-y][0-9][A-CEG-HJ-NPR-TV-Za-ceg-hj-npr-tv-z] ?[0-9][A-CEG-HJ-NPR-TV-Za-ceg-hj-npr-tv-z][0-9])\\Z"
        ),
        None,
        (),
    ),
    "isStrongPassword": (
        8,
        None,
        None,
        None,
        (
            re.compile("[A-Z]"),
            re.compile("[a-z]"),
            re.compile("[0-9]"),
            re.compile("[!-/:-@\\[-`{-\\~]"),
        ),
    ),
    "hasLowercase": (0, None, None, None, (re.compile("[a-z]"),)),
    "hasUppercase": (0, None, None, None, (re.compile("[A-Z]"),)),
    "hasNumbers": (0, None, None, None, (re.compile("[0-9]"),)),
    "isNotEmpty": (
        0,
        None,
        None,
        None,
        (
            re.compile(
                "[\\u0001-\\u0008\\u000E-\\u001F!-\\u0084\\u0086-\\u009F\\u00A1-\\u167F\\u1681-\\u1FFF\\u200B-\\u2027\\u202A-\\u202E\\u2030-\\u205E\\u2060-\\u2FFF\\u3001-\\uD7FF\\uE000-\\U0010FFFF]"
            ),
        ),
    ),
}


def _cruftfree_matches_validator_format(method: str, value: object) -> bool:
    """Whether *value* passes ``Validator.<method>``: a text within bounds, matching, passing the
    format's check, containing each required part.

    A value that is not a text passes no check. The length bound is checked
    before any pattern, so a pattern only ever reads a bounded value.
    """
    min_length, max_length, pattern, check, required = _CRUFTFREE_VALIDATOR_FORMATS[
        method
    ]
    if not isinstance(value, str) or len(value) < min_length:
        return False
    if max_length is not None and len(value) > max_length:
        return False
    if pattern is not None and pattern.fullmatch(value) is None:
        return False
    if check is not None and not check(value):
        return False
    return all(part.search(value) is not None for part in required)
