"""The regex tree and the bounds of the pattern language."""

from __future__ import annotations

import string
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

from cruftfree_common.builtins.regex_code_points import (
    CodePointRanges,
    code_point_ranges_union,
    normalize_code_point_ranges,
)

#: The most capturing groups a pattern holds: the most PostgreSQL's replacements reach.
MAX_CAPTURING_GROUPS: Final[int] = 9
#: The largest quantifier bound: PostgreSQL's ``RE_DUP_MAX``.
MAX_REPEAT_BOUND: Final[int] = 255
#: The builtin regex members, as ``Category.member``, that act on every match found
#: in their input; every other regex member tests the whole value.
FOUND_REGEX_OPERATIONS: Final[frozenset[str]] = frozenset(
    {"String.replaceRegex", "Regex.findAll", "Regex.replace"}
)


def _check_span(node: str, span: tuple[int, int]) -> None:
    start, end = span
    if not 0 <= start <= end:
        raise ValueError(
            f"{node} span {span} is not [start, end) offsets; write 0 <= start <= end"
        )


@dataclass(frozen=True)
class CodePointSet:
    """A set of code points, one of which the input holds at this place."""

    ranges: CodePointRanges
    """Inclusive ranges, sorted, disjoint and non-adjacent; never empty."""
    span: tuple[int, int]

    def __post_init__(self) -> None:
        _check_span("CodePointSet", self.span)
        if not self.ranges or normalize_code_point_ranges(self.ranges) != self.ranges:
            raise ValueError(
                f"CodePointSet ranges {self.ranges} are not one set; write them non-empty, "
                "inside the domain, sorted, disjoint and non-adjacent (normalize_code_point_ranges)"
            )


@dataclass(frozen=True)
class Sequence:
    """Two or more parts the input holds one after another."""

    items: tuple[RegexNode, ...]
    span: tuple[int, int]

    def __post_init__(self) -> None:
        _check_span("Sequence", self.span)
        if len(self.items) < 2:
            raise ValueError(
                f"Sequence has {len(self.items)} items; a sequence holds two or more"
            )


@dataclass(frozen=True)
class Alternation:
    """Two or more alternatives, the first one that matches taken."""

    alternatives: tuple[RegexNode, ...]
    span: tuple[int, int]

    def __post_init__(self) -> None:
        _check_span("Alternation", self.span)
        if len(self.alternatives) < 2:
            raise ValueError(
                f"Alternation has {len(self.alternatives)} alternatives; an alternation holds two or more"
            )


@dataclass(frozen=True)
class Group:
    """A capturing group: its body, its number and its name."""

    body: RegexNode
    number: int
    """1-based, by opening parenthesis among the capturing groups."""
    name: str | None
    span: tuple[int, int]

    def __post_init__(self) -> None:
        _check_span("Group", self.span)
        if not 1 <= self.number <= MAX_CAPTURING_GROUPS:
            raise ValueError(
                f"Group number {self.number} is outside 1-{MAX_CAPTURING_GROUPS}"
            )


@dataclass(frozen=True)
class Repeat:
    """Its body, greedily repeated from ``low`` to ``high`` times."""

    body: RegexNode
    low: int
    high: int | None
    """``None`` for no upper bound."""
    span: tuple[int, int]

    def __post_init__(self) -> None:
        _check_span("Repeat", self.span)
        high = MAX_REPEAT_BOUND if self.high is None else self.high
        if not 0 <= self.low <= high <= MAX_REPEAT_BOUND or high < 1:
            raise ValueError(
                f"Repeat bounds ({self.low}, {self.high}) are outside the language; write "
                f"0 <= low <= high <= {MAX_REPEAT_BOUND} with high at least 1, or high None"
            )


@dataclass(frozen=True)
class Anchor:
    """The start or the end of the whole input, never of a line."""

    edge: Literal["start", "end"]
    span: tuple[int, int]

    def __post_init__(self) -> None:
        _check_span("Anchor", self.span)


#: Every node of a pattern tree.
RegexNode = CodePointSet | Sequence | Alternation | Group | Repeat | Anchor


@dataclass(frozen=True)
class RegexPattern:
    """A read pattern: its tree, how many capturing groups it has and the number of each named one."""

    root: RegexNode
    group_count: int
    group_names: Mapping[str, int]
    span: tuple[int, int]

    def __post_init__(self) -> None:
        _check_span("RegexPattern", self.span)
        if not 0 <= self.group_count <= MAX_CAPTURING_GROUPS:
            raise ValueError(
                f"RegexPattern group count {self.group_count} is outside 0-{MAX_CAPTURING_GROUPS}"
            )
        outside = sorted(
            name
            for name, number in self.group_names.items()
            if not 1 <= number <= self.group_count
        )
        if outside:
            raise ValueError(
                f"RegexPattern names {outside} number no group of the {self.group_count}; "
                "a named group's number is one of the pattern's groups"
            )
        object.__setattr__(
            self, "group_names", MappingProxyType(dict(self.group_names))
        )


class RegexPatternError(ValueError):
    """A pattern outside the regex pattern language."""

    def __init__(
        self, pattern: str, position: int, construct: str, supported: str
    ) -> None:
        self.pattern = pattern
        self.position = position
        """0-based code-point offset of the construct in the pattern."""
        self.construct = construct
        """What the pattern has there (``a lookahead``, ``an unescaped '-' at a set's edge``)."""
        self.supported = supported
        """The supported form to write instead."""
        super().__init__(
            f"Regex pattern {pattern!r} has {construct} at position {position + 1}; write {supported}"
        )


#: The 32 ASCII punctuation characters ``\\`` turns into themselves.
_ESCAPABLE_PUNCTUATION: Final[frozenset[str]] = frozenset(string.punctuation)
#: The control escapes, by the letter after the backslash.
_CONTROL_ESCAPES: Final[Mapping[str, int]] = MappingProxyType(
    {"n": 0x0A, "t": 0x09, "r": 0x0D}
)
_CODE_POINT_ESCAPE_LETTER: Final[str] = "u"
_CODE_POINT_ESCAPE_DIGITS: Final[int] = 4
_HEX_DIGITS: Final[frozenset[str]] = frozenset(string.hexdigits)
_DECIMAL_DIGITS: Final[frozenset[str]] = frozenset(string.digits)
_ASCII_LETTERS: Final[frozenset[str]] = frozenset(string.ascii_letters)
_GROUP_NAME_CHARACTERS: Final[frozenset[str]] = frozenset(
    string.ascii_letters + string.digits + "_"
)
#: The quantifier characters and the bounds each stands for.
_QUANTIFIER_BOUNDS: Final[Mapping[str, tuple[int, int | None]]] = MappingProxyType(
    {"*": (0, None), "+": (1, None), "?": (0, 1)}
)
#: What follows the last item of an alternative: the end, a ``|`` or a group's ``)``.
_ALTERNATIVE_ENDS: Final[frozenset[str]] = frozenset({"", "|", ")"})
#: What may follow ``$`` at the end of a top-level alternative.
_TOP_LEVEL_ALTERNATIVE_ENDS: Final[frozenset[str]] = frozenset({"", "|"})
#: The code points ``[`` opens a POSIX class or collating element with.
_POSIX_CLASS_OPENERS: Final[frozenset[str]] = frozenset({":", "=", "."})
#: The smallest code point after a backslash that is neither a space nor a control.
_FIRST_VISIBLE_ASCII: Final[int] = 0x21
_LAST_VISIBLE_ASCII: Final[int] = 0x7E
_NUL: Final[int] = 0x00
_SURROGATE_LOW: Final[int] = 0xD800
_SURROGATE_HIGH: Final[int] = 0xDFFF

_SUPPORTED_ESCAPES: Final[str] = (
    "'\\' before ASCII punctuation, \\uHHHH, \\n, \\t, \\r, \\d, \\w, \\s, \\D, \\W or \\S"
)
_FOUR_HEX_DIGITS: Final[str] = "\\uHHHH with exactly four hex digits"
_ASTRAL_AS_ITSELF: Final[str] = "\\uHHHH, or an astral code point written as itself"
_NO_LOOKAROUND: Final[str] = "a pattern without lookaround, or a check in code"
_SPELLED_SET: Final[str] = (
    "\\d, \\w, \\s or a set spelling its code points, such as [A-Za-z]"
)
_REFUSED_BACKREFERENCE: Final[tuple[str, str]] = (
    "a backreference or octal escape",
    "\\uHHHH for a code point, or a check in code that compares two parts",
)
_REFUSED_INPUT_EDGE: Final[tuple[str, str]] = (
    "an input-edge escape",
    "'^' or '$' at the start or end of a top-level alternative",
)
_REFUSED_WORD_BOUNDARY: Final[tuple[str, str]] = (
    "a word-boundary escape",
    "a set of the code points on each side, or a check in code",
)
_REFUSED_PROPERTY_CLASS: Final[tuple[str, str]] = ("a property class", _SPELLED_SET)

#: The escapes outside the language that are named for what they are elsewhere:
#: the kind of escape and the supported form to write instead, by the character after ``\\``.
_REFUSED_ESCAPES: Final[Mapping[str, tuple[str, str]]] = MappingProxyType(
    {
        "b": _REFUSED_WORD_BOUNDARY,
        "B": _REFUSED_WORD_BOUNDARY,
        "A": _REFUSED_INPUT_EDGE,
        "z": _REFUSED_INPUT_EDGE,
        "Z": _REFUSED_INPUT_EDGE,
        "G": _REFUSED_INPUT_EDGE,
        "f": ("a form-feed escape", "\\u000C"),
        "v": ("a vertical-tab escape", "\\u000B"),
        "c": ("a control escape", "\\uHHHH"),
        "x": ("a two-digit hex escape", _FOUR_HEX_DIGITS),
        "U": ("an eight-digit code-point escape", _ASTRAL_AS_ITSELF),
        "k": ("a named backreference", "a check in code that compares the two parts"),
        "p": _REFUSED_PROPERTY_CLASS,
        "P": _REFUSED_PROPERTY_CLASS,
        **{digit: _REFUSED_BACKREFERENCE for digit in string.digits},
    }
)


@dataclass(frozen=True)
class _BraceShape:
    """A ``{...}`` that has the shape of a quantifier, its bounds still unchecked."""

    low: str
    """The lower bound's digits (empty for ``{,m}``)."""
    high: str | None
    """The upper bound's digits, ``""`` for ``{n,}``, ``None`` for ``{n}``."""
    end: int
    """The offset after the ``}``."""


#: No code point: what an anchor starts with, and what follows the whole pattern.
_NO_CODE_POINTS: Final[CodePointRanges] = ()
#: How many ranges of an overlap a refusal spells out before counting the rest.
_MOST_RANGES_NAMED: Final[int] = 3

_EMPTY_BODY: Final[str] = "a varying repetition whose body can match the empty string"
_EMPTY_BODY_REWRITE: Final[str] = (
    "a repeated part that matches at least one code point, such as a* for (?:a?)*"
)
_BODY_MEETS_FOLLOW_REWRITE: Final[str] = (
    "a repetition and what follows it starting with different code points, such as "
    "[^b]*b for .*b, or one repetition for both, such as \\d{2,} for \\d+\\d+"
)
_ALTERNATIVES_MEET_REWRITE: Final[str] = (
    "alternatives starting with different code points, their shared start written "
    "once, such as ab? for a|ab"
)


def _code_point_name(code_point: int) -> str:
    """*code_point* as itself in quotes when it is visible ASCII, else as ``U+HHHH``."""
    if _FIRST_VISIBLE_ASCII <= code_point <= _LAST_VISIBLE_ASCII:
        return f"'{chr(code_point)}'"
    return f"U+{code_point:04X}"


def _named_code_points(ranges: CodePointRanges) -> str:
    """The first ranges of *ranges* spelled out, and how many more there are."""
    names = [
        _code_point_name(low)
        if low == high
        else f"{_code_point_name(low)}-{_code_point_name(high)}"
        for low, high in ranges[:_MOST_RANGES_NAMED]
    ]
    rest = len(ranges) - _MOST_RANGES_NAMED
    if rest <= 0:
        return ", ".join(names)
    plural = "s" if rest > 1 else ""
    return f"{', '.join(names)} and {rest} more range{plural}"


def _is_varying(node: Repeat) -> bool:
    """Whether *node*'s count varies: ``* + ?``, ``{n,}``, ``{n,m}`` with ``n < m``."""
    return node.high is None or node.low < node.high


class _StartSets:
    """What each node of one read tree can start with, each node worked out once.

    A node's start is whether it can match the empty string (an anchor counting as
    empty) and the code points it can begin with (an anchor adding none).
    """

    def __init__(self) -> None:
        self._starts: dict[int, tuple[bool, CodePointRanges]] = {}

    def start(self, node: RegexNode) -> tuple[bool, CodePointRanges]:
        """Whether *node* can match the empty string, and the code points it can start with."""
        key = id(node)
        if key not in self._starts:
            self._starts[key] = self._start_of(node)
        return self._starts[key]

    def _start_of(self, node: RegexNode) -> tuple[bool, CodePointRanges]:
        if isinstance(node, CodePointSet):
            return False, node.ranges
        if isinstance(node, Anchor):
            return True, _NO_CODE_POINTS
        if isinstance(node, Group):
            return self.start(node.body)
        if isinstance(node, Repeat):
            nullable, first = self.start(node.body)
            return nullable or node.low == 0, first
        if isinstance(node, Alternation):
            starts = [self.start(alternative) for alternative in node.alternatives]
            return (
                any(nullable for nullable, _ in starts),
                code_point_ranges_union(*(first for _, first in starts)),
            )
        return self._sequence_start(node)

    def _sequence_start(self, node: Sequence) -> tuple[bool, CodePointRanges]:
        firsts: list[CodePointRanges] = []
        for item in node.items:
            nullable, first = self.start(item)
            firsts.append(first)
            if not nullable:
                return False, code_point_ranges_union(*firsts)
        return True, code_point_ranges_union(*firsts)
