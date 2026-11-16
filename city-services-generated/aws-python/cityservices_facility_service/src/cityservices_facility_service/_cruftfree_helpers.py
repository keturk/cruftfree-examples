"""Small runtime helpers for generated CruftFree service code."""

from __future__ import annotations

import base64
import binascii
import datetime
import decimal
import enum
import math
import os
import re
from collections.abc import AsyncGenerator, Callable, Iterable, Sequence
from contextlib import aclosing
from typing import NoReturn, TypeVar

_OptionalReceiver = TypeVar("_OptionalReceiver")
_OptionalMember = TypeVar("_OptionalMember")
_Element = TypeVar("_Element")
_Key = TypeVar("_Key")
_Folded = TypeVar("_Folded")

# ``DateTime.parse(value, pattern)``/``Validator.isDate(value, pattern)``: the
# shared parse pattern language every target reads.
#: Each token of the parse pattern language, as ``(token, field, fewest digits,
#: most digits, value when the pattern omits it, smallest value, largest value)``.
#: The day's largest value is further bounded by the length of its month.
DATE_PARSE_TOKENS: tuple[tuple[str, str, int, int, int, int, int], ...] = (
    ("yyyy", "year", 4, 4, 1900, 1, 9999),
    ("MM", "month", 1, 2, 1, 1, 12),
    ("dd", "day", 1, 2, 1, 1, 31),
    ("HH", "hour", 1, 2, 0, 0, 23),
    ("mm", "minute", 1, 2, 0, 0, 59),
    ("ss", "second", 1, 2, 0, 0, 59),
)

#: The tokens as an error message names them.
DATE_PARSE_TOKEN_LIST: str = " ".join(row[0] for row in DATE_PARSE_TOKENS)

_DATE_PATTERN_QUOTE = "'"
_DATE_PATTERN_ESCAPED_QUOTE = "\\'"


class DateParsePatternError(ValueError):
    """A date parse pattern outside the pattern language."""


def _date_parse_quoted(pattern: str, text: str, index: int) -> tuple[str, int]:
    """The literal text of the quote opening at *index* of *text*, and the index after it."""
    end = text.find(_DATE_PATTERN_QUOTE, index + 1)
    if end == -1:
        raise DateParsePatternError(
            f"Date pattern {pattern!r} has an unterminated quote"
        )
    literal = _DATE_PATTERN_QUOTE if end == index + 1 else text[index + 1 : end]
    return literal, end + 1


def _date_parse_token_at(
    pattern: str, text: str, index: int, fields: list[str]
) -> tuple[str, int, int, int, int, int, int] | None:
    """The token starting at *index* of *text*, or ``None``; a token already read is an error."""
    row = next(
        (
            candidate
            for candidate in DATE_PARSE_TOKENS
            if text.startswith(candidate[0], index)
        ),
        None,
    )
    if row is not None and row[1] in fields:
        raise DateParsePatternError(
            f"Date pattern {pattern!r} uses the token {row[0]!r} twice; each field may be read once"
        )
    return row


def date_parse_expression(pattern: str) -> tuple[re.Pattern[str], tuple[str, ...]]:
    """The expression a value written by *pattern* matches, and the field each of its groups reads, in order.

    Raises:
        DateParsePatternError: *pattern* has an unquoted letter that is not a
            token, an unterminated quote, or a token it already used.
    """
    text = pattern.replace(_DATE_PATTERN_ESCAPED_QUOTE, _DATE_PATTERN_QUOTE)
    source: list[str] = []
    fields: list[str] = []
    index = 0
    while index < len(text):
        row = _date_parse_token_at(pattern, text, index, fields)
        if row is not None:
            fields.append(row[1])
            source.append(f"([0-9]{{{row[2]},{row[3]}}})")
            index += len(row[0])
            continue
        char = text[index]
        if char == _DATE_PATTERN_QUOTE:
            literal, index = _date_parse_quoted(pattern, text, index)
            source.append(re.escape(literal))
            continue
        if char.isascii() and char.isalpha():
            raise DateParsePatternError(
                f"Date pattern {pattern!r} has the unquoted letter {char!r}; the tokens are "
                f"{DATE_PARSE_TOKEN_LIST}, and any other text must be written in single quotes"
            )
        source.append(re.escape(char))
        index += 1
    return re.compile("".join(source)), tuple(fields)


def read_date_with_pattern(value: str, pattern: str) -> datetime.datetime | None:
    """*value* read as written by *pattern*, as a UTC instant; ``None`` when it does not match.

    Raises:
        DateParsePatternError: *pattern* is outside the pattern language.
    """
    expression, fields = date_parse_expression(pattern)
    match = expression.fullmatch(value)
    if match is None:
        return None
    read = dict(zip(fields, (int(group) for group in match.groups()), strict=True))
    parts: dict[str, int] = {}
    for _token, field, _fewest, _most, omitted, smallest, largest in DATE_PARSE_TOKENS:
        number = read[field] if field in read else omitted
        if not smallest <= number <= largest:
            return None
        parts[field] = number
    try:
        return datetime.datetime(
            parts["year"],
            parts["month"],
            parts["day"],
            parts["hour"],
            parts["minute"],
            parts["second"],
            tzinfo=datetime.timezone.utc,
        )
    except ValueError:
        # A day past the end of its month (31 April, 29 February of a common year).
        return None


#: The tokens ``DateTime.format(pattern)`` renders, with the ``strftime``
#: directive each stands for: the pattern language every target reads, in its
#: order. Longer tokens come first so ``yyyy`` is never read as two ``yy``. Every
#: other character of a pattern is a literal. ``%B``/``%b``/``%p`` are English
#: under the C locale a generated service runs in.
_CRUFTFREE_FORMAT_PATTERN_TOKENS: tuple[tuple[str, str], ...] = (
    ("YYYY", "%Y"),
    ("yyyy", "%Y"),
    ("yy", "%y"),
    ("MMMM", "%B"),
    ("MMM", "%b"),
    ("MM", "%m"),
    ("DD", "%d"),
    ("dd", "%d"),
    ("HH", "%H"),
    ("hh", "%I"),
    ("mm", "%M"),
    ("ss", "%S"),
    ("a", "%p"),
)


def _cruftfree_pattern_to_strftime(pattern: str) -> str:
    """The ``strftime`` format for a CruftFree ``DateTime.format`` *pattern*.

    Recognized tokens are ``yyyy`` (or ``YYYY``) ``yy`` ``MMMM`` ``MMM`` ``MM``
    ``dd`` (or ``DD``) ``HH`` ``hh`` ``mm`` ``ss`` ``a``. Text in single quotes
    is a literal (``''`` is a literal quote); punctuation and whitespace outside
    quotes are literals too; any other ASCII letter outside quotes is an error,
    so a pattern means the same on every target.

    Raises:
        ValueError: *pattern* has an unquoted letter that is not a token, or an
            unterminated quote.
    """
    pattern = pattern.replace("\\'", "'")  # a quote escaped inside a DSL string literal
    out: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        token = next(
            (
                (t, d)
                for t, d in _CRUFTFREE_FORMAT_PATTERN_TOKENS
                if pattern.startswith(t, index)
            ),
            None,
        )
        if token is not None:
            out.append(token[1])
            index += len(token[0])
        elif char == "'":
            end = pattern.find("'", index + 1)
            if end == -1:
                raise ValueError(f"Date pattern {pattern!r} has an unterminated quote")
            literal = "'" if end == index + 1 else pattern[index + 1 : end]
            out.append(literal.replace("%", "%%"))
            index = end + 1
        elif char.isascii() and char.isalpha():
            raise ValueError(
                f"Date pattern {pattern!r} has the unquoted letter {char!r}; the tokens are "
                "YYYY yyyy yy MMMM MMM MM DD dd HH hh mm ss a, and any other text must be written in single quotes"
            )
        else:
            out.append("%%" if char == "%" else char)
            index += 1
    return "".join(out)


def _cruftfree_format_datetime(value: datetime.date, pattern: str) -> str:
    """Render *value* as written by the CruftFree *pattern*.

    Raises:
        ValueError: *pattern* is not a valid CruftFree date pattern.
    """
    return value.strftime(_cruftfree_pattern_to_strftime(pattern))


_CRUFTFREE_HASH_ALGORITHMS: dict[str, str] = {
    "SHA256": "sha256",
    "SHA1": "sha1",
    "MD5": "md5",
    "SHA512": "sha512",
}


def _cruftfree_hash_algorithm(name: str) -> str:
    """The ``hashlib`` name of the CruftFree hash algorithm *name* (any letter case).

    Raises:
        ValueError: *name* is not one of the supported algorithms.
    """
    algorithm = _CRUFTFREE_HASH_ALGORITHMS.get(name.upper())
    if algorithm is None:
        raise ValueError(
            f"Unsupported hash algorithm {name!r}; valid algorithms: {sorted(_CRUFTFREE_HASH_ALGORITHMS)}"
        )
    return algorithm


#: ``Crypto.encrypt``/``Crypto.decrypt``, the same scheme on every target: AES-256-GCM
#: with no associated data. The key is 32 bytes in base64url (43 characters, optionally
#: one trailing ``=``); the ciphertext is unpadded base64url of nonce, ciphertext, tag.
_CRUFTFREE_CIPHER_KEY_BYTES = 32
_CRUFTFREE_CIPHER_NONCE_BYTES = 12
_CRUFTFREE_CIPHER_TAG_BYTES = 16
_CRUFTFREE_CIPHER_KEY_TEXT = re.compile(r"[A-Za-z0-9_-]{43}=?")
_CRUFTFREE_CIPHERTEXT_TEXT = re.compile(r"[A-Za-z0-9_-]+")
_CRUFTFREE_CIPHER_KEY_ERROR = (
    "Crypto key must be 32 bytes written in base64url: 43 characters of A-Z a-z 0-9 - _, "
    "optionally followed by one '='. Generate it from 32 random bytes and keep it in a secret."
)
_CRUFTFREE_CIPHERTEXT_ERROR = (
    "Crypto.decrypt: the value is not a ciphertext this key produced; it is malformed, "
    "was altered, or was encrypted under another key."
)


def _cruftfree_base64url(text: str, pattern: re.Pattern[str], error: str) -> bytes:
    """The bytes *text* encodes in canonical base64url; ``ValueError(error)`` for anything else."""
    if pattern.fullmatch(text) is None:
        raise ValueError(error)
    unpadded = text.rstrip("=")
    try:
        raw = base64.urlsafe_b64decode(unpadded + "=" * (-len(unpadded) % 4))
    except binascii.Error as exc:
        raise ValueError(error) from exc
    if base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != unpadded:
        raise ValueError(error)
    return raw


def _cruftfree_cipher_key(key: str) -> bytes:
    """The AES-256 key *key* writes in base64url; ``ValueError`` for any other text."""
    secret = _cruftfree_base64url(
        key, _CRUFTFREE_CIPHER_KEY_TEXT, _CRUFTFREE_CIPHER_KEY_ERROR
    )
    if len(secret) != _CRUFTFREE_CIPHER_KEY_BYTES:
        raise ValueError(_CRUFTFREE_CIPHER_KEY_ERROR)
    return secret


def _cruftfree_encrypt(plaintext: str, key: str) -> str:
    """``Crypto.encrypt``: AES-256-GCM under a fresh random nonce.

    Raises:
        ValueError: *key* is not 32 bytes in base64url.
    """
    # The cipher library is a dependency only of services that encrypt.
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(_CRUFTFREE_CIPHER_NONCE_BYTES)
    sealed = AESGCM(_cruftfree_cipher_key(key)).encrypt(
        nonce, plaintext.encode("utf-8"), None
    )
    return base64.urlsafe_b64encode(nonce + sealed).decode("ascii").rstrip("=")


def _cruftfree_decrypt(ciphertext: str, key: str) -> str:
    """``Crypto.decrypt``: authenticate and decrypt a ``Crypto.encrypt`` value.

    Raises:
        ValueError: *key* is not 32 bytes in base64url, or *ciphertext* is malformed,
            altered, or was encrypted under another key.
    """
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    secret = _cruftfree_cipher_key(key)
    sealed = _cruftfree_base64url(
        ciphertext, _CRUFTFREE_CIPHERTEXT_TEXT, _CRUFTFREE_CIPHERTEXT_ERROR
    )
    if len(sealed) < _CRUFTFREE_CIPHER_NONCE_BYTES + _CRUFTFREE_CIPHER_TAG_BYTES:
        raise ValueError(_CRUFTFREE_CIPHERTEXT_ERROR)
    nonce, body = (
        sealed[:_CRUFTFREE_CIPHER_NONCE_BYTES],
        sealed[_CRUFTFREE_CIPHER_NONCE_BYTES:],
    )
    try:
        return AESGCM(secret).decrypt(nonce, body, None).decode("utf-8")
    except InvalidTag as exc:
        raise ValueError(_CRUFTFREE_CIPHERTEXT_ERROR) from exc


def _cruftfree_parse_datetime(value: str, pattern: str) -> datetime.datetime:
    """``DateTime.parse(value, pattern)``: *value* read as written by *pattern*, as a UTC instant.

    Raises:
        ValueError: *value* does not match *pattern*, or *pattern* is outside the
            parse pattern language.
    """
    parsed = read_date_with_pattern(value, pattern)
    if parsed is None:
        raise ValueError(
            f"DateTime.parse: {value!r} does not match the pattern {pattern!r}"
        )
    return parsed


def _cruftfree_fail(message: str) -> NoReturn:
    """Raise *message* where an expression cannot continue (an unmatched ``match``).

    Raises:
        RuntimeError: always.
    """
    raise RuntimeError(message)


def _cruftfree_remainder(
    dividend: int | float | decimal.Decimal, divisor: int | float | decimal.Decimal
) -> int | float | decimal.Decimal:
    """The CruftFree remainder ``%`` / ``Math.mod``: it takes the dividend's sign
    (``-7 % 3`` is ``-1``, ``7 % -3`` is ``1``), as on every target.

    Python's ``%`` on numbers takes the divisor's sign instead. A ``Decimal``'s
    ``%`` already takes the dividend's; two integers stay an integer.
    """
    if isinstance(dividend, decimal.Decimal) or isinstance(divisor, decimal.Decimal):
        return dividend % divisor
    if isinstance(dividend, int) and isinstance(divisor, int):
        magnitude = abs(dividend) % abs(divisor)
        return -magnitude if dividend < 0 else magnitude
    return math.fmod(dividend, divisor)


def _cruftfree_str(value: object) -> str:
    """String conversion matching CruftFree DSL concatenation semantics."""
    if value is None:
        return ""
    if isinstance(value, enum.Enum):
        return str(value.value)
    if isinstance(value, decimal.Decimal):
        text = format(value.normalize(), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    if isinstance(value, float):
        return _cruftfree_number_text(value)
    return str(value)


def _cruftfree_number_text(value: float | decimal.Decimal) -> str:
    """A floating-point value as ECMAScript ``Number::toString`` text, the same on every target.

    The digits are the shortest that read back as *value* (``repr``'s); they are
    laid out in plain notation for 1e-6 <= |value| < 1e21 and as ``d[.ddd]e±n``
    otherwise. A whole value has no fraction (``10``), ``-0.0`` reads ``0``, and the
    non-finite values read ``NaN``, ``Infinity`` and ``-Infinity``.

    A ``Percentage``, ``Latitude`` or ``Longitude`` read from its ``Numeric`` column
    arrives as a ``Decimal``; it reads as the double it is typed as, so ``Decimal('75.50')``
    and ``75.5`` give the same text.
    """
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "0"
    if value < 0:
        return "-" + _cruftfree_number_text(-value)
    _sign, digit_tuple, exponent = decimal.Decimal(repr(value)).as_tuple()
    digits = "".join(str(digit) for digit in digit_tuple).rstrip("0")
    # The value is 0.<digits> x 10**point.
    point = len(digit_tuple) + int(exponent)
    if len(digits) <= point <= 21:
        return digits + "0" * (point - len(digits))
    if 0 < point <= 21:
        return digits[:point] + "." + digits[point:]
    if -6 < point <= 0:
        return "0." + "0" * -point + digits
    power = point - 1
    mantissa = digits if len(digits) == 1 else digits[0] + "." + digits[1:]
    return f"{mantissa}e{'+' if power >= 0 else '-'}{abs(power)}"


def _cruftfree_format_number(
    value: int | float | decimal.Decimal, fraction_digits: int, grouping: bool
) -> str:
    """``Number.format``: *value* as fixed-point text with *fraction_digits* fraction digits.

    Locale-neutral: ``.`` before the fraction and, with *grouping*, ``,`` between
    groups of three integer digits. A float reads as its shortest round-trip
    decimal text, an exact tie rounds to the even neighbour, and a negative that
    rounds to zero has no sign: the same text on every target.

    Raises:
        ValueError: *fraction_digits* is negative or not a whole number, or *value*
            is not finite.
    """
    if (
        isinstance(fraction_digits, bool)
        or not isinstance(fraction_digits, int)
        or fraction_digits < 0
    ):
        raise ValueError(
            f"Number.format needs a whole, non-negative number of fraction digits; got {fraction_digits!r}."
        )
    exact = value if isinstance(value, decimal.Decimal) else decimal.Decimal(str(value))
    if not exact.is_finite():
        raise ValueError(f"Number.format cannot format {value!r}, which is not finite.")
    with decimal.localcontext() as context:
        context.rounding = decimal.ROUND_HALF_EVEN
        text = format(exact, f"{',' if grouping else ''}.{fraction_digits}f")
    return (
        text.removeprefix("-")
        if text.startswith("-") and not any(char in "123456789" for char in text)
        else text
    )


def _cruftfree_index_of(items: Sequence[object], value: object) -> int:
    """``Array.indexOf``: the position of the first item equal to *value*, or -1 when none is.

    ``list.index`` raises ``ValueError`` for an absent value; the builtin answers -1
    on every target.
    """
    for index, item in enumerate(items):
        if item == value:
            return index
    return -1


def _cruftfree_last_index_of(items: Sequence[object], value: object) -> int:
    """``Array.lastIndexOf``: the position of the last item equal to *value*, or -1 when none is.

    ``list.index`` raises ``ValueError`` for an absent value; the builtin answers -1
    on every target.
    """
    for index in range(len(items) - 1, -1, -1):
        if items[index] == value:
            return index
    return -1


async def _cruftfree_first_of(
    values: AsyncGenerator[_Element, None], default: _Element
) -> _Element:
    """The first value *values* produces, or *default* when it produces none.

    An ``Array`` row that stops early over a callback that awaits: *values* awaits
    one element at a time, so the elements after the deciding one are never called.
    """
    async with aclosing(values) as remaining:
        async for value in remaining:
            return value
    return default


async def _cruftfree_collect(values: AsyncGenerator[_Element, None]) -> list[_Element]:
    """``Array.filter``/``flatMap`` over a callback that awaits: every value, in order."""
    return [value async for value in values]


async def _cruftfree_sorted_by(
    keyed: AsyncGenerator[tuple[_Key, _Element], None],
) -> list[_Element]:
    """``Array.sortBy`` over a key that awaits: every key awaited in element order,
    then a stable sort, so elements of equal key keep their order."""
    pairs = [pair async for pair in keyed]
    return [item for _key, item in sorted(pairs, key=lambda pair: pair[0])]


async def _cruftfree_grouped_by(
    keyed: AsyncGenerator[tuple[_Key, _Element], None],
) -> dict[_Key, list[_Element]]:
    """``Array.groupBy`` over a key that awaits: groups in the order their keys first
    appear, each holding its elements in order."""
    groups: dict[_Key, list[_Element]] = {}
    async for key, item in keyed:
        groups.setdefault(key, []).append(item)
    return groups


async def _cruftfree_fold(
    step: Callable[[_Folded, _Element], AsyncGenerator[_Folded, None]],
    items: Iterable[_Element],
    initial: _Folded,
) -> _Folded:
    """``Array.reduce`` over a reducer that awaits, each step awaiting the one before.

    A Python lambda cannot await, so *step* answers a one-value asynchronous generator.
    """
    folded = initial
    for item in items:
        async with aclosing(step(folded, item)) as value:
            folded = await anext(value)
    return folded


def _cruftfree_optional_read(
    receiver: _OptionalReceiver | None,
    read: Callable[[_OptionalReceiver], _OptionalMember],
) -> _OptionalMember | None:
    """``receiver?.member`` on a computed receiver: ``read(receiver)``, or ``None``
    when *receiver* is ``None``.

    The receiver arrives already evaluated, so a call or an ``await`` in it runs
    once, as the optional chain runs it on every target. Valid in every expression
    position, a comprehension's iterable included, where binding the receiver with
    ``:=`` is not.
    """
    if receiver is None:
        return None
    return read(receiver)


def _cruftfree_float_or_none(
    value: decimal.Decimal | float | int | str | None,
) -> float | None:
    """A nullable DSL number bound to a ``Float?`` slot: ``None`` flows through unchanged.

    Accepts a ``Decimal``, ``int``, ``float`` or a numeric string -- the form a
    Decimal-origin number takes after crossing a service boundary as JSON, since
    ``_json_helpers._json_default`` encodes ``decimal.Decimal`` as a string.
    """
    if value is None:
        return None
    return float(value)


def _cruftfree_decimal_or_none(
    value: decimal.Decimal | float | int | str | None,
) -> decimal.Decimal | None:
    """A nullable DSL number bound to a ``Decimal?`` slot: ``None`` flows through unchanged.

    Converts through ``str`` so a float's shortest round-trip repr is what the
    Decimal carries, never the binary expansion ``decimal.Decimal(0.1)`` would;
    a numeric string (JSON-encoded Decimal) parses as written.
    """
    if value is None:
        return None
    return decimal.Decimal(str(value))


def _cruftfree_int_or_none(value: float | int | str | None) -> int | None:
    """A nullable JSON number bound to an ``Integer?`` slot: ``None`` flows through unchanged."""
    if value is None:
        return None
    return int(value)


def _cruftfree_minor_units(amount: object) -> object:
    """A payment gateway amount as the whole number of minor units its client takes.

    A ``Money`` amount scaled to cents (``payment.amount.amount * 100``) is a
    ``decimal.Decimal``; an integral ``Decimal`` or ``float`` becomes the ``int``
    it equals. A value with a fractional part is never truncated: it is returned
    unchanged, and the gateway client refuses it (``invalid_amount``).
    """
    if isinstance(amount, bool) or not isinstance(amount, (decimal.Decimal, float)):
        return amount
    finite = (
        amount.is_finite()
        if isinstance(amount, decimal.Decimal)
        else math.isfinite(amount)
    )
    if not finite:
        return amount
    whole = int(amount)
    return whole if whole == amount else amount


def _cruftfree_exc_message(exc: BaseException) -> str:
    """Message for a DSL ``<exception>.message`` read, including the cause chain.

    ``str(exc)`` alone is empty for the whole family of exceptions that carry
    their detail in ``__cause__`` rather than in their own args.  Every ``httpx``
    transport error is built that way -- ``httpx`` raises ``mapped_exc(str(inner))
    from inner`` over an ``httpcore`` error which in turn wraps an ``anyio``
    exception with empty args -- so a peer that closes the connection during the
    TLS handshake and a name-resolution failure both render as ``ConnectError('')``
    and cannot be told apart by whoever reads the log.

    When the exception carries a message of its own it is returned unchanged, so
    every message that has content today is byte-identical.  Only the provably
    contentless case walks the chain, preferring ``__cause__`` (explicit
    ``raise ... from ...``) over ``__context__`` (implicit chaining, which is how
    ``httpcore``'s ``map_exceptions`` and several stdlib paths chain), and renders
    each hop's class name plus whatever detail that hop does carry.

    The walk is guarded by an identity set: a handler that re-raises an exception
    it caught can produce a cyclic chain, and an unguarded walk would not
    terminate.
    """
    text = str(exc)
    if text:
        return text
    chain = [type(exc).__name__]
    seen = {id(exc)}
    current: BaseException = exc
    while True:
        nxt = current.__cause__ or current.__context__
        if nxt is None or id(nxt) in seen:
            return " <- ".join(chain)
        seen.add(id(nxt))
        current = nxt
        detail = str(current)
        name = type(current).__name__
        chain.append(f"{name}({detail})" if detail else name)


# ``String.padStart``/``padEnd``: the shared padding rule every target realizes.
def _padding(text: str, length: int, fill: str) -> str:
    """The characters that bring *text* to *length*: *fill* repeated, cut to fit."""
    missing = length - len(text)
    if missing <= 0 or fill == "":
        return ""
    return (fill * (missing // len(fill) + 1))[:missing]


def pad_start(text: str, length: int, fill: str = " ") -> str:
    """*text* with *fill* repeated before it until it is *length* long."""
    return _padding(text, length, fill) + text


def pad_end(text: str, length: int, fill: str = " ") -> str:
    """*text* with *fill* repeated after it until it is *length* long."""
    return text + _padding(text, length, fill)


# ``String.substring``/``charAt``/``trim``/``trimStart``/``trimEnd``/``isBlank``:
# the shared index and whitespace rules every target realizes.
#: Unicode ``White_Space`` by code point: TAB..CR, SPACE, NEL, NBSP, OGHAM SPACE
#: MARK, EN QUAD..HAIR SPACE, LINE SEPARATOR, PARAGRAPH SEPARATOR, NARROW NBSP,
#: MEDIUM MATHEMATICAL SPACE, IDEOGRAPHIC SPACE. Built from code points so no
#: line or paragraph separator ever appears literally in source.
TEXT_WHITE_SPACE_CODE_POINTS = (
    *range(0x09, 0x0E),
    0x20,
    0x85,
    0xA0,
    0x1680,
    *range(0x2000, 0x200B),
    0x2028,
    0x2029,
    0x202F,
    0x205F,
    0x3000,
)

#: The same set as text, for ``str.strip``.
TEXT_WHITE_SPACE = "".join(chr(code) for code in TEXT_WHITE_SPACE_CODE_POINTS)

#: The same set as a bracket set of the regex pattern language (``\s`` reads to it).
TEXT_WHITE_SPACE_CLASS = "[\\u0009-\\u000d\\u0020\\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]"


def _clamped(index: int, length: int) -> int:
    return min(max(index, 0), length)


def text_substring(text: str, start: int, end: int | None = None) -> str:
    """The code points from *start* to *end*: each bound clamped to the text, a reversed pair swapped."""
    length = len(text)
    first = _clamped(start, length)
    last = length if end is None else _clamped(end, length)
    if first > last:
        first, last = last, first
    return text[first:last]


def text_char_at(text: str, index: int) -> str:
    """The code point at *index*.

    Raises:
        IndexError: *index* is outside ``[0, length)`` (a negative index never
            counts from the end).
    """
    if not 0 <= index < len(text):
        raise IndexError(
            f"String.charAt index {index} is outside the text of {len(text)} characters; "
            "pass an index from 0 to the length minus one"
        )
    return text[index]


def text_trim(text: str) -> str:
    """*text* without its leading and trailing Unicode ``White_Space``."""
    return text.strip(TEXT_WHITE_SPACE)


def text_trim_start(text: str) -> str:
    """*text* without its leading Unicode ``White_Space``."""
    return text.lstrip(TEXT_WHITE_SPACE)


def text_trim_end(text: str) -> str:
    """*text* without its trailing Unicode ``White_Space``."""
    return text.rstrip(TEXT_WHITE_SPACE)


def text_is_blank(text: str) -> bool:
    """True when *text* is empty or holds only Unicode ``White_Space``."""
    return text.strip(TEXT_WHITE_SPACE) == ""


def text_capitalize(text: str) -> str:
    """*text* with its first code point upper-cased and the rest lower-cased."""
    return text[:1].upper() + text[1:].lower()


def text_title(text: str) -> str:
    """*text* with every space-separated word capitalized (:func:`text_capitalize`)."""
    return " ".join(text_capitalize(word) for word in text.split(" "))


# ``String.replaceRegex`` and ``Regex.replace``: the replacement template syntax every target reads.
#: The two-character references that name a fixed part of the match.
_FIXED_REFERENCES = ("$", "&", "`", "'")


def regex_replace_all(text: str, pattern: re.Pattern[str], replacement: str) -> str:
    """*text* with every match of *pattern* replaced by the expanded *replacement* template.

    *pattern* is compiled at generation from the read pattern tree; the author's
    pattern text never reaches ``re`` here.
    """
    return pattern.sub(lambda match: regex_substitution(replacement, match), text)


def regex_substitution(replacement: str, match: re.Match[str]) -> str:
    """The replacement template *replacement* expanded for one *match*."""
    parts: list[str] = []
    position = 0
    while position < len(replacement):
        dollar = replacement.find("$", position)
        if dollar < 0 or dollar == len(replacement) - 1:
            parts.append(replacement[position:])
            break
        parts.append(replacement[position:dollar])
        expanded, consumed = _reference_at(replacement, dollar, match)
        parts.append(expanded)
        position = dollar + consumed
    return "".join(parts)


def _is_ascii_digit(character: str) -> bool:
    return "0" <= character <= "9"


def _reference_at(replacement: str, at: int, match: re.Match[str]) -> tuple[str, int]:
    """The text the ``$`` reference at *at* stands for, and how many characters it spans."""
    follower = replacement[at + 1]
    if follower in _FIXED_REFERENCES:
        return _fixed_reference(follower, match), 2
    if _is_ascii_digit(follower):
        return _numbered_reference(replacement, at, match)
    if follower == "<":
        return _named_reference(replacement, at, match)
    return "$", 1


def _fixed_reference(follower: str, match: re.Match[str]) -> str:
    if follower == "$":
        return "$"
    if follower == "&":
        return match.group(0)
    if follower == "`":
        return match.string[: match.start()]
    return match.string[match.end() :]


def _numbered_reference(
    replacement: str, at: int, match: re.Match[str]
) -> tuple[str, int]:
    group_count = match.re.groups
    two_digits = at + 2 < len(replacement) and _is_ascii_digit(replacement[at + 2])
    digits = 2 if two_digits else 1
    index = int(replacement[at + 1 : at + 1 + digits])
    if digits == 2 and index > group_count:
        digits = 1
        index = int(replacement[at + 1])
    if 1 <= index <= group_count:
        return match.group(index) or "", 1 + digits
    return replacement[at : at + 1 + digits], 1 + digits


def _named_reference(
    replacement: str, at: int, match: re.Match[str]
) -> tuple[str, int]:
    close = replacement.find(">", at + 2)
    if not match.re.groupindex or close < 0:
        return "$<", 2
    name = replacement[at + 2 : close]
    return match.groupdict().get(name) or "", close - at + 1
