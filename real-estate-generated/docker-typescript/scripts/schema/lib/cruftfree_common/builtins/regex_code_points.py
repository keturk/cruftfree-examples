"""The code-point sets of the regex pattern language, as inclusive ranges.

A set is a tuple of inclusive ``(low, high)`` code-point ranges, sorted, disjoint
and non-adjacent, so one set has exactly one spelling and two sets compare equal
exactly when they hold the same code points. Every set ranges over the domain
U+0001-U+10FFFF without the surrogates U+D800-U+DFFF (PostgreSQL text holds no
U+0000, and no target string holds a lone surrogate): normalizing a range that
crosses an excluded code point leaves that code point out, and a complement is
taken within the domain.

The class escapes are fixed sets, the same on every target: ``\\d`` is ``0``-``9``
and ``\\w`` is ``A``-``Z a``-``z 0``-``9 _`` (ASCII, because Unicode's digit and
letter sets grow each version and every engine ships its own), ``\\s`` is the
Unicode ``White_Space`` set ``String.trim`` reads, and ``.`` is every code point
but U+000A. The upper-case escapes are their complements.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Final

from cruftfree_common.builtins.text_units import TEXT_WHITE_SPACE_CODE_POINTS

__all__ = [
    "ANY_BUT_LINE_FEED",
    "CODE_POINT_DOMAIN",
    "DIGIT",
    "NOT_DIGIT",
    "NOT_WHITE_SPACE",
    "NOT_WORD",
    "REGEX_CLASS_ESCAPES",
    "WHITE_SPACE",
    "WORD",
    "CodePointRanges",
    "code_point_ranges_complement",
    "code_point_ranges_contain",
    "code_point_ranges_intersection",
    "code_point_ranges_union",
    "normalize_code_point_ranges",
]

#: A code-point set: inclusive ranges, sorted, disjoint and non-adjacent.
CodePointRanges = tuple[tuple[int, int], ...]

#: The largest Unicode code point.
_MAX_CODE_POINT: Final[int] = 0x10FFFF
#: The first and last surrogate code point.
_SURROGATE_LOW: Final[int] = 0xD800
_SURROGATE_HIGH: Final[int] = 0xDFFF
#: U+000A, the one code point ``.`` does not match.
_LINE_FEED: Final[int] = 0x0A

#: Every code point a set may hold: U+0001-U+10FFFF without the surrogates.
CODE_POINT_DOMAIN: Final[CodePointRanges] = (
    (0x01, _SURROGATE_LOW - 1),
    (_SURROGATE_HIGH + 1, _MAX_CODE_POINT),
)


def _clipped_to_domain(low: int, high: int) -> list[tuple[int, int]]:
    """The parts of ``[low, high]`` inside :data:`CODE_POINT_DOMAIN`."""
    parts: list[tuple[int, int]] = []
    for domain_low, domain_high in CODE_POINT_DOMAIN:
        part_low = max(low, domain_low)
        part_high = min(high, domain_high)
        if part_low <= part_high:
            parts.append((part_low, part_high))
    return parts


def normalize_code_point_ranges(ranges: Iterable[tuple[int, int]]) -> CodePointRanges:
    """*ranges* as one set: clipped to the domain, sorted, overlapping and adjacent ranges merged.

    Raises:
        ValueError: a range has its low end above its high end, or an end outside
            U+0000-U+10FFFF.
    """
    clipped: list[tuple[int, int]] = []
    for low, high in ranges:
        if not 0 <= low <= high <= _MAX_CODE_POINT:
            raise ValueError(
                f"Code-point range ({low:#x}, {high:#x}) is not a range of code points; "
                f"each end must lie in 0x0-{_MAX_CODE_POINT:#x} with the low end not above the high end"
            )
        clipped.extend(_clipped_to_domain(low, high))
    merged: list[tuple[int, int]] = []
    for low, high in sorted(clipped):
        if merged and low <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return tuple(merged)


def code_point_ranges_union(*sets: CodePointRanges) -> CodePointRanges:
    """Every code point held by any of *sets*."""
    return normalize_code_point_ranges(
        code_range for ranges in sets for code_range in ranges
    )


def code_point_ranges_intersection(
    first: CodePointRanges, second: CodePointRanges
) -> CodePointRanges:
    """Every code point held by both normalized sets *first* and *second*."""
    shared: list[tuple[int, int]] = []
    left = right = 0
    while left < len(first) and right < len(second):
        low = max(first[left][0], second[right][0])
        high = min(first[left][1], second[right][1])
        if low <= high:
            shared.append((low, high))
        if first[left][1] < second[right][1]:
            left += 1
        else:
            right += 1
    return tuple(shared)


def code_point_ranges_complement(ranges: CodePointRanges) -> CodePointRanges:
    """Every code point of :data:`CODE_POINT_DOMAIN` that *ranges* does not hold."""
    gaps: list[tuple[int, int]] = []
    next_low = 0
    for low, high in normalize_code_point_ranges(ranges):
        if next_low < low:
            gaps.append((next_low, low - 1))
        next_low = high + 1
    if next_low <= _MAX_CODE_POINT:
        gaps.append((next_low, _MAX_CODE_POINT))
    return normalize_code_point_ranges(gaps)


def code_point_ranges_contain(ranges: CodePointRanges, code_point: int) -> bool:
    """Whether the normalized set *ranges* holds *code_point*."""
    index = bisect_right(ranges, (code_point, _MAX_CODE_POINT)) - 1
    return index >= 0 and ranges[index][0] <= code_point <= ranges[index][1]


#: ``.``: every code point but U+000A.
ANY_BUT_LINE_FEED: Final[CodePointRanges] = code_point_ranges_complement(
    ((_LINE_FEED, _LINE_FEED),)
)
#: ``\d``: the ASCII digits.
DIGIT: Final[CodePointRanges] = normalize_code_point_ranges(((ord("0"), ord("9")),))
#: ``\w``: the ASCII letters, digits and ``_``.
WORD: Final[CodePointRanges] = normalize_code_point_ranges(
    (
        (ord("0"), ord("9")),
        (ord("A"), ord("Z")),
        (ord("_"), ord("_")),
        (ord("a"), ord("z")),
    )
)
#: ``\s``: Unicode ``White_Space``, the set ``String.trim`` removes.
WHITE_SPACE: Final[CodePointRanges] = normalize_code_point_ranges(
    (code_point, code_point) for code_point in TEXT_WHITE_SPACE_CODE_POINTS
)
#: ``\D``, ``\W``, ``\S``: the complements.
NOT_DIGIT: Final[CodePointRanges] = code_point_ranges_complement(DIGIT)
NOT_WORD: Final[CodePointRanges] = code_point_ranges_complement(WORD)
NOT_WHITE_SPACE: Final[CodePointRanges] = code_point_ranges_complement(WHITE_SPACE)

#: The class escapes by the letter after the backslash.
REGEX_CLASS_ESCAPES: Final[Mapping[str, CodePointRanges]] = MappingProxyType(
    {
        "d": DIGIT,
        "D": NOT_DIGIT,
        "w": WORD,
        "W": NOT_WORD,
        "s": WHITE_SPACE,
        "S": NOT_WHITE_SPACE,
    }
)
