"""Identifier case conversion and length caps, on the standard library only.

The word splitter every case function shares, snake_case and PascalCase, and the
truncation that keeps a capped identifier distinct. Code that runs after
generation imports these from here, so it never reaches a third-party package.
"""

from __future__ import annotations

import functools
import hashlib
import re
from typing import Final

__all__ = [
    "DB_MAX_IDENTIFIER_LENGTH",
    "split_words",
    "to_pascal_case",
    "to_snake_case",
    "truncate_db_identifier",
    "truncate_identifier",
]

# ── Identifier Length Caps ──

#: PostgreSQL's identifier limit, the cap every database identifier CruftFree derives is held to.
DB_MAX_IDENTIFIER_LENGTH = 63
_HASH_SUFFIX_LENGTH = 8


# @canonical(text/identifier-length-cap): Cap an identifier's length without
# letting two distinct names collapse onto one value.
# A length limit constrains an identifier's ENCODING; it is not a licence to
# drop the part that makes the identifier distinct. Identifiers are built
# most-general-first (``<scope>-<scope>-<thing>``), so the discriminating
# component sits at the END -- which is exactly what a bare ``name[:n]`` cuts.
# Uniqueness then holds only by accident of naming, and fails the first time
# two names share a long prefix.
# @rule: The digest is taken over the FULL, untruncated name, so two inputs
#   sharing a prefix cannot share a suffix.
# @rule: A name already within the limit is returned unchanged, so short names
#   never churn when the cap is introduced or widened.
# @anti-pattern: ``name[:MAX]`` / ``f"{a}-{b}-{c}"[:MAX]`` on any value that
#   identifies a resource (index, constraint, dashboard UID, topic,
#   subscription, configuration set, generated function name).
# @see: text/db-identifier-length-cap
def truncate_identifier(
    name: str,
    max_length: int,
    *,
    separator: str = "_",
    trailing: str = "",
) -> str:
    """Cap *name* at *max_length* while keeping distinct names distinct.

    Args:
        name: Full, untruncated identifier body.
        max_length: Maximum allowed length of the returned identifier.
        separator: Character(s) joining the truncated body, the digest and
            *trailing* -- match the identifier's own convention (``_`` for SQL
            and Python identifiers, ``-`` for kebab-cased resource names).
        trailing: Component that must survive at the END of the result -- a
            kind marker such as ``svc`` that distinguishes two otherwise
            identical identifiers by shape. Appended to *name* to form the
            full identifier, and re-appended after truncation so it is never
            the thing that gets cut. Empty means no trailing component.

    Returns:
        The full identifier unchanged when it already fits, otherwise
        ``<truncated-body><sep><digest>[<sep><trailing>]`` -- at most
        *max_length* characters.

    Raises:
        ValueError: If *max_length* leaves no room for a body once the digest
            and *trailing* are reserved.
    """
    full = f"{name}{separator}{trailing}" if trailing else name
    if len(full) <= max_length:
        return full
    reserved = len(separator) + _HASH_SUFFIX_LENGTH
    if trailing:
        reserved += len(separator) + len(trailing)
    body_length = max_length - reserved
    if body_length < 1:
        raise ValueError(
            f"Cannot cap identifier {full!r} at {max_length} characters: the "
            f"{_HASH_SUFFIX_LENGTH}-character uniqueness digest"
            + (f" and the mandatory {trailing!r} suffix" if trailing else "")
            + f" already reserve {reserved} characters, leaving no room for the "
            "identifier itself. Raise max_length, shorten the trailing "
            "component, or drop it."
        )
    digest = hashlib.sha256(full.encode("utf-8")).hexdigest()[:_HASH_SUFFIX_LENGTH]
    parts = [name[:body_length], digest]
    if trailing:
        parts.append(trailing)
    return separator.join(parts)


# @canonical(text/db-identifier-length-cap): PostgreSQL identifier cap.
# Pure pre-binding of text/identifier-length-cap to PostgreSQL's 63-character
# limit and underscore convention -- no second implementation of the algorithm.
def truncate_db_identifier(
    name: str,
    max_length: int = DB_MAX_IDENTIFIER_LENGTH,
) -> str:
    """Truncate a database identifier to *max_length*, preserving uniqueness.

    PostgreSQL silently truncates identifiers to 63 characters, and
    SQLAlchemy raises ``IdentifierError`` when a name exceeds the limit.
    When the generated name is within the limit it is returned unchanged.
    Otherwise the name is truncated and an 8-character hex hash of the
    full name is appended so that distinct long names remain distinct.

    Args:
        name: The identifier name (constraint, index, etc.).
        max_length: Maximum allowed length (default 63 for PostgreSQL).

    Returns:
        The name unchanged if within *max_length*, or a truncated name
        with a hash suffix (e.g. ``uq_very_long_table_na_3f2a91c0``).
    """
    return truncate_identifier(name, max_length, separator="_")


# ── Word Splitting ──

_WORD_BOUNDARY_RE = re.compile(
    r"""
    (?<=[a-z0-9])(?=[A-Z])        # camelCase boundary: aB -> a|B
    | (?<=[A-Z])(?=[A-Z][a-z])    # acronym boundary: ABc -> A|Bc
    | [.\-_\s]+                   # explicit separators: dot, hyphen, underscore, space
    """,
    re.VERBOSE,
)


def split_words(text: str) -> list[str]:
    """Split text into words by case boundaries and separators.

    Handles camelCase, PascalCase, SCREAMING_SNAKE_CASE, kebab-case,
    snake_case, dot.separated, space separated, and acronyms.

    Args:
        text: Input text (str or PolyString; PolyString is converted via str()).

    Returns:
        List of lowercase words

    Examples:
        >>> split_words("HTMLParser")
        ['html', 'parser']
        >>> split_words("library.BookService")
        ['library', 'book', 'service']
        >>> split_words("my-service")
        ['my', 'service']
    """
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return []
    return list(_split_words_of(str(text)))


#: How many distinct texts :func:`_split_words_of` remembers. Generation asks for
#: the same few thousand names over and over; the bound keeps a long-lived
#: process (the language server) from growing the cache without limit.
_SPLIT_WORDS_CACHE_SIZE: Final[int] = 65536


@functools.lru_cache(maxsize=_SPLIT_WORDS_CACHE_SIZE)
def _split_words_of(text: str) -> tuple[str, ...]:
    """The lowercase words of *text* (a plain ``str``), computed once per text."""
    return tuple(p.lower() for p in _WORD_BOUNDARY_RE.split(text) if p)


# ── Case Conversion ──


def to_snake_case(text: str) -> str:
    """Convert text to snake_case.

    All separators (dots, hyphens, underscores, spaces) and case boundaries
    are normalized to underscores.

    Args:
        text: Input text (PascalCase, camelCase, kebab-case, dot.separated, etc.)

    Returns:
        snake_case version

    Examples:
        >>> to_snake_case("UserProfile")
        'user_profile'
        >>> to_snake_case("HTMLParser")
        'html_parser'
        >>> to_snake_case("library.BookService")
        'library_book_service'
        >>> to_snake_case("my-service")
        'my_service'
    """
    words = split_words(text)
    return "_".join(words) if words else ""


def to_pascal_case(text: str) -> str:
    """Convert text to PascalCase.

    Args:
        text: Input text (snake_case, camelCase, kebab-case, etc.)

    Returns:
        PascalCase version

    Examples:
        >>> to_pascal_case("user_profile")
        'UserProfile'
        >>> to_pascal_case("library.BookService")
        'LibraryBookService'
    """
    words = split_words(text)
    if not words:
        return ""
    return "".join(w.capitalize() for w in words)
