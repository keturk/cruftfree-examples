"""The pattern reader of the regex pattern language."""

from __future__ import annotations

from typing import NoReturn

from cruftfree_common.builtins._regex_determinism import _DeterminismCheck
from cruftfree_common.builtins._regex_nodes import (
    _ALTERNATIVE_ENDS,
    _ASCII_LETTERS,
    _ASTRAL_AS_ITSELF,
    _CODE_POINT_ESCAPE_DIGITS,
    _CODE_POINT_ESCAPE_LETTER,
    _CONTROL_ESCAPES,
    _DECIMAL_DIGITS,
    _ESCAPABLE_PUNCTUATION,
    _FIRST_VISIBLE_ASCII,
    _FOUR_HEX_DIGITS,
    _GROUP_NAME_CHARACTERS,
    _HEX_DIGITS,
    _LAST_VISIBLE_ASCII,
    _NO_LOOKAROUND,
    _NUL,
    _POSIX_CLASS_OPENERS,
    _QUANTIFIER_BOUNDS,
    _REFUSED_ESCAPES,
    _SPELLED_SET,
    _SUPPORTED_ESCAPES,
    _SURROGATE_HIGH,
    _SURROGATE_LOW,
    _TOP_LEVEL_ALTERNATIVE_ENDS,
    MAX_CAPTURING_GROUPS,
    MAX_REPEAT_BOUND,
    Alternation,
    Anchor,
    CodePointSet,
    Group,
    RegexNode,
    RegexPattern,
    RegexPatternError,
    Repeat,
    Sequence,
    _BraceShape,
)
from cruftfree_common.builtins.regex_code_points import (
    ANY_BUT_LINE_FEED,
    REGEX_CLASS_ESCAPES,
    CodePointRanges,
    code_point_ranges_complement,
    code_point_ranges_union,
    normalize_code_point_ranges,
)


class _PatternReader:
    """One left-to-right read of a pattern, refusing at the first construct outside the language."""

    def __init__(self, pattern: str) -> None:
        self._pattern = pattern
        self._position = 0
        self._group_count = 0
        self._group_names: dict[str, int] = {}

    def read(self) -> RegexPattern:
        if not self._pattern:
            self._refuse_empty_pattern()
        root = self._alternation(group_start=None)
        _DeterminismCheck(self._pattern).check(root)
        return RegexPattern(
            root=root,
            group_count=self._group_count,
            group_names=self._group_names,
            span=(0, len(self._pattern)),
        )

    # -- reading position --------------------------------------------------

    def _peek(self, ahead: int = 0) -> str:
        """The code point *ahead* places after the read position, ``""`` past the end."""
        index = self._position + ahead
        return self._pattern[index : index + 1]

    def _refuse(self, position: int, construct: str, supported: str) -> NoReturn:
        raise RegexPatternError(self._pattern, position, construct, supported)

    def _refuse_empty_pattern(self) -> NoReturn:
        self._refuse(0, "the empty pattern", "a pattern of at least one code point")

    # -- alternation, alternative, term -----------------------------------

    def _alternation(self, group_start: int | None) -> RegexNode:
        """The alternatives up to the end (top level) or the group's ``)``."""
        start = self._position
        alternatives: list[RegexNode] = []
        bar: int | None = None
        while True:
            alternative = self._alternative(top_level=group_start is None)
            if alternative is None:
                self._refuse_empty_alternative(group_start, bar)
            alternatives.append(alternative)
            if self._peek() != "|":
                break
            bar = self._position
            self._position += 1
        if len(alternatives) == 1:
            return alternatives[0]
        return Alternation(tuple(alternatives), (start, self._position))

    def _refuse_empty_alternative(
        self, group_start: int | None, bar: int | None
    ) -> NoReturn:
        """Refuse an alternative holding nothing, at the ``|`` next to it.

        With no ``|`` around it, the alternative is the whole group, or the whole pattern.
        """
        if self._peek() == "|":
            bar = self._position
        if bar is not None:
            self._refuse(
                bar,
                "an empty alternative",
                "an alternative of at least one code point, or no '|' there",
            )
        if group_start is not None:
            self._refuse(
                group_start,
                "an empty group",
                "a group around at least one code point, or no group",
            )
        self._refuse_empty_pattern()

    def _alternative(self, top_level: bool) -> RegexNode | None:
        """The items up to the alternative's end, or ``None`` when it holds none."""
        start = self._position
        items: list[RegexNode] = []
        if top_level and self._peek() == "^":
            items.append(Anchor("start", (start, start + 1)))
            self._position += 1
        while not self._ends_alternative(top_level):
            items.append(self._item(top_level))
        if not items:
            return None
        if len(items) == 1:
            return items[0]
        return Sequence(tuple(items), (start, self._position))

    def _ends_alternative(self, top_level: bool) -> bool:
        char = self._peek()
        if char == ")" and top_level:
            self._refuse(
                self._position,
                "an unmatched ')'",
                "'\\)' for a literal ')', or the group's opening '('",
            )
        return char in _ALTERNATIVE_ENDS

    def _item(self, top_level: bool) -> RegexNode:
        start = self._position
        if (
            top_level
            and self._peek() == "$"
            and self._peek(1) in _TOP_LEVEL_ALTERNATIVE_ENDS
        ):
            self._position += 1
            return Anchor("end", (start, start + 1))
        atom = self._atom()
        bounds = self._quantifier()
        if bounds is None:
            return atom
        self._refuse_stacked_quantifier()
        return Repeat(atom, bounds[0], bounds[1], (start, self._position))

    # -- atoms -------------------------------------------------------------

    def _atom(self) -> RegexNode:
        start = self._position
        char = self._peek()
        if char == "(":
            return self._group()
        if char == "[":
            return self._set()
        if char == "\\":
            ranges, _ = self._escape()
            return CodePointSet(ranges, (start, self._position))
        if char == ".":
            self._position += 1
            return CodePointSet(ANY_BUT_LINE_FEED, (start, self._position))
        self._refuse_syntax_outside_set(char, start)
        code_point = self._literal_code_point(char, start)
        self._position += 1
        return CodePointSet(((code_point, code_point),), (start, self._position))

    def _refuse_syntax_outside_set(self, char: str, start: int) -> None:
        if char in _QUANTIFIER_BOUNDS or (
            char == "{" and self._brace_shape(start) is not None
        ):
            self._refuse(
                start,
                "a quantifier with nothing to repeat",
                "the quantifier after the part it repeats; '\\' before it for the literal character",
            )
        if char == "{":
            self._refuse(
                start,
                "an unescaped '{' that forms no quantifier",
                "'\\{' for a literal '{'",
            )
        if char == "}":
            self._refuse(start, "an unescaped '}'", "'\\}' for a literal '}'")
        if char == "]":
            self._refuse(start, "an unescaped ']'", "'\\]' for a literal ']'")
        if char == "^":
            self._refuse(
                start,
                "a '^' that is not at the start of a top-level alternative",
                "'^' first in the pattern or right after a top-level '|'; '\\^' for a literal '^'",
            )
        if char == "$":
            self._refuse(
                start,
                "a '$' that is not at the end of a top-level alternative",
                "'$' last in the pattern or right before a top-level '|'; '\\$' for a literal '$'",
            )

    def _literal_code_point(self, char: str, position: int) -> int:
        """*char* as a code point of the language, refusing U+0000 and a surrogate."""
        code_point = ord(char)
        self._check_code_point(code_point, position)
        return code_point

    def _check_code_point(self, code_point: int, position: int) -> None:
        if code_point == _NUL:
            self._refuse(
                position,
                "U+0000",
                "a pattern without U+0000; PostgreSQL text holds none",
            )
        if _SURROGATE_LOW <= code_point <= _SURROGATE_HIGH:
            self._refuse(
                position,
                f"the surrogate U+{code_point:04X}",
                "an astral code point written as itself",
            )

    # -- escapes -----------------------------------------------------------

    def _escape(self) -> tuple[CodePointRanges, int | None]:
        """The escape at the read position: its set, and its code point when it is one."""
        start = self._position
        char = self._peek(1)
        if not char:
            self._refuse(start, "a final '\\'", "'\\\\' for a literal '\\'")
        if char in _ESCAPABLE_PUNCTUATION:
            return self._single_code_point(ord(char), start + 2)
        if char in _CONTROL_ESCAPES:
            return self._single_code_point(_CONTROL_ESCAPES[char], start + 2)
        if char in REGEX_CLASS_ESCAPES:
            self._position = start + 2
            return REGEX_CLASS_ESCAPES[char], None
        if char == _CODE_POINT_ESCAPE_LETTER:
            return self._code_point_escape(start)
        self._refuse_escape(start, char)

    def _single_code_point(
        self, code_point: int, end: int
    ) -> tuple[CodePointRanges, int]:
        self._position = end
        return ((code_point, code_point),), code_point

    def _code_point_escape(self, start: int) -> tuple[CodePointRanges, int]:
        digits_start = start + 2
        digits = self._pattern[digits_start : digits_start + _CODE_POINT_ESCAPE_DIGITS]
        if digits[:1] == "{":
            self._refuse(start, "a braced code-point escape '\\u{'", _ASTRAL_AS_ITSELF)
        if len(digits) != _CODE_POINT_ESCAPE_DIGITS or not set(digits) <= _HEX_DIGITS:
            self._refuse(
                start, "a '\\u' escape without four hex digits", _FOUR_HEX_DIGITS
            )
        code_point = int(digits, 16)
        self._check_code_point(code_point, start)
        return self._single_code_point(
            code_point, digits_start + _CODE_POINT_ESCAPE_DIGITS
        )

    def _refuse_escape(self, start: int, char: str) -> NoReturn:
        if char in _REFUSED_ESCAPES:
            kind, supported = _REFUSED_ESCAPES[char]
            self._refuse(start, f"{kind} '\\{char}'", supported)
        code_point = ord(char)
        if not _FIRST_VISIBLE_ASCII <= code_point <= _LAST_VISIBLE_ASCII:
            self._refuse(
                start,
                f"a '\\' before U+{code_point:04X}",
                "the code point itself, or \\uHHHH",
            )
        self._refuse(start, f"an unsupported escape '\\{char}'", _SUPPORTED_ESCAPES)

    # -- sets --------------------------------------------------------------

    def _set(self) -> CodePointSet:
        start = self._position
        self._position += 1
        negated = self._peek() == "^"
        if negated:
            self._position += 1
        if self._peek() == "]":
            self._refuse(
                start,
                "a set with no member",
                "at least one code point between '[' and ']'; '\\]' for a literal ']'",
            )
        members_start = self._position
        members: list[CodePointRanges] = []
        while self._peek() != "]":
            members.append(self._set_member(start, members_start))
        self._position += 1
        ranges = code_point_ranges_union(*members)
        if negated:
            ranges = code_point_ranges_complement(ranges)
        if not ranges:
            self._refuse(
                start, "a set matching nothing", "a set holding at least one code point"
            )
        return CodePointSet(ranges, (start, self._position))

    def _set_member(self, set_start: int, members_start: int) -> CodePointRanges:
        """One member of a set: a code point, a class escape or a range."""
        low_start = self._position
        ranges, low = self._set_atom(set_start, members_start)
        if self._peek() != "-":
            return ranges
        dash = self._position
        if self._peek(1) == "]":
            self._refuse_edge_dash(dash)
        if low is None:
            self._refuse_dash_forming_no_range(dash)
        self._position += 1
        high_start = self._position
        _, high = self._set_atom(set_start, members_start)
        if high is None:
            self._refuse(
                high_start,
                "a range ending at a class escape",
                "a range between two code points, and the class as its own member",
            )
        if low > high:
            self._refuse(
                low_start,
                "a range whose low end is above its high end",
                "the range low end first, such as a-z",
            )
        return normalize_code_point_ranges(((low, high),))

    def _set_atom(
        self, set_start: int, members_start: int
    ) -> tuple[CodePointRanges, int | None]:
        """A code point or class escape inside a set."""
        start = self._position
        char = self._peek()
        if not char:
            self._refuse(
                set_start, "a '[' with no closing ']'", "the set's closing ']'"
            )
        if char == "\\":
            return self._escape()
        if char == "-":
            if start == members_start:
                self._refuse_edge_dash(start)
            self._refuse_dash_forming_no_range(start)
        if char == "[":
            self._refuse_bracket_in_set(start)
        if char == "^":
            self._refuse(
                start,
                "an unescaped '^' inside a set",
                "'\\^' for a literal '^'; '[^' only to open a complement",
            )
        return self._single_code_point(self._literal_code_point(char, start), start + 1)

    def _refuse_edge_dash(self, position: int) -> NoReturn:
        self._refuse(
            position, "an unescaped '-' at a set's edge", "'\\-' for a literal '-'"
        )

    def _refuse_dash_forming_no_range(self, position: int) -> NoReturn:
        self._refuse(
            position,
            "an unescaped '-' that forms no range",
            "'\\-' for a literal '-', or a range between two code points such as a-z",
        )

    def _refuse_bracket_in_set(self, position: int) -> NoReturn:
        opener = self._peek(1)
        if opener in _POSIX_CLASS_OPENERS:
            self._refuse(position, f"a POSIX class '[{opener}'", _SPELLED_SET)
        self._refuse(
            position, "an unescaped '[' inside a set", "'\\[' for a literal '['"
        )

    # -- groups ------------------------------------------------------------

    def _group(self) -> RegexNode:
        start = self._position
        self._position += 1
        capturing, name = self._group_head(start)
        number = self._number_group(start, name) if capturing else 0
        body = self._alternation(group_start=start)
        if self._peek() != ")":
            self._refuse_unclosed_group(start)
        self._position += 1
        if not capturing:
            return body
        return Group(body, number, name, (start, self._position))

    def _refuse_unclosed_group(self, start: int) -> NoReturn:
        self._refuse(start, "a '(' with no closing ')'", "the group's closing ')'")

    def _number_group(self, start: int, name: str | None) -> int:
        self._group_count += 1
        if self._group_count > MAX_CAPTURING_GROUPS:
            self._refuse(
                start,
                "a tenth capturing group",
                f"at most {MAX_CAPTURING_GROUPS} capturing groups; (?:...) for a group that captures nothing",
            )
        if name is not None:
            if name in self._group_names:
                self._refuse(
                    start,
                    f"a second group named '{name}'",
                    "a name of its own for each group",
                )
            self._group_names[name] = self._group_count
        return self._group_count

    def _group_head(self, start: int) -> tuple[bool, str | None]:
        """Whether the group just opened captures, and its name; the read position moves past ``(?:`` / ``(?<name>``."""
        if self._peek() != "?":
            return True, None
        marker = self._peek(1)
        after = self._peek(2)
        if marker == ":":
            self._position += 2
            return False, None
        if marker == "<" and after not in {"=", "!"}:
            self._position += 2
            return True, self._group_name()
        self._refuse_group_form(start, marker, after)

    def _group_name(self) -> str:
        start = self._position
        end = start
        while self._pattern[end : end + 1] in _GROUP_NAME_CHARACTERS:
            end += 1
        name = self._pattern[start:end]
        if name[:1] not in _ASCII_LETTERS or self._pattern[end : end + 1] != ">":
            self._refuse(
                start,
                "a group name that is not an ASCII letter followed by ASCII letters, digits or '_'",
                "(?<name>...) with a name such as orderId",
            )
        self._position = end + 1
        return name

    def _refuse_group_form(self, start: int, marker: str, after: str) -> NoReturn:
        if marker in {"=", "!"}:
            self._refuse(start, f"a lookahead '(?{marker}'", _NO_LOOKAROUND)
        if marker == "<":
            self._refuse(start, f"a lookbehind '(?<{after}'", _NO_LOOKAROUND)
        if marker == ">":
            self._refuse(start, "an atomic group '(?>'", "a plain group (?:...)")
        if marker == "P":
            self._refuse(start, "a Python-style named group '(?P'", "(?<name>...)")
        if marker in _ASCII_LETTERS or marker in {"-", "^"}:
            self._refuse(
                start,
                f"an inline flag group '(?{marker}'",
                "no flags: a set spelling both cases, such as [Pp], or code matching String.toLowerCase of the value",
            )
        if not marker:
            self._refuse_unclosed_group(start)
        self._refuse(
            start,
            f"an unsupported group form '(?{marker}'",
            "(...), (?:...) or (?<name>...)",
        )

    # -- quantifiers -------------------------------------------------------

    def _quantifier(self) -> tuple[int, int | None] | None:
        """The quantifier at the read position, if any, its bounds checked; the position moves past it."""
        char = self._peek()
        if char in _QUANTIFIER_BOUNDS:
            self._position += 1
            return _QUANTIFIER_BOUNDS[char]
        if char != "{":
            return None
        start = self._position
        shape = self._brace_shape(start)
        if shape is None:
            return None
        bounds = self._brace_bounds(start, shape)
        self._position = shape.end
        return bounds

    def _brace_shape(self, start: int) -> _BraceShape | None:
        """The ``{...}`` at *start* when it has a quantifier's shape (digits, a comma, digits, ``}``)."""
        low_end = self._digits_end(start + 1)
        position = low_end
        high: str | None = None
        if self._pattern[position : position + 1] == ",":
            high_end = self._digits_end(position + 1)
            high = self._pattern[position + 1 : high_end]
            position = high_end
        low = self._pattern[start + 1 : low_end]
        if self._pattern[position : position + 1] != "}" or (not low and high is None):
            return None
        return _BraceShape(low, high, position + 1)

    def _digits_end(self, start: int) -> int:
        end = start
        while self._pattern[end : end + 1] in _DECIMAL_DIGITS:
            end += 1
        return end

    def _brace_bounds(self, start: int, shape: _BraceShape) -> tuple[int, int | None]:
        if not shape.low:
            self._refuse(start, "a quantifier with no lower bound", "{0,m}")
        written = [shape.low] if not shape.high else [shape.low, shape.high]
        if any(len(bound) > 1 and bound.startswith("0") for bound in written):
            self._refuse(
                start,
                "a quantifier bound with a leading zero",
                "the bound without leading zeros, such as {1}",
            )
        if any(int(bound) > MAX_REPEAT_BOUND for bound in written):
            self._refuse(
                start,
                f"a quantifier bound above {MAX_REPEAT_BOUND}",
                f"a bound of at most {MAX_REPEAT_BOUND}",
            )
        low = int(shape.low)
        high = low if shape.high is None else (int(shape.high) if shape.high else None)
        if high is not None and low > high:
            self._refuse(
                start,
                "a quantifier whose lower bound is above its upper bound",
                "{n,m} with n at most m",
            )
        if high == 0:
            self._refuse(
                start,
                "a quantifier whose upper bound is 0",
                "an upper bound of at least 1, or no such part",
            )
        return low, high

    def _refuse_stacked_quantifier(self) -> None:
        position = self._position
        char = self._peek()
        if char == "?":
            self._refuse(
                position, "a lazy quantifier", "the greedy quantifier, without the '?'"
            )
        if char == "+":
            self._refuse(
                position,
                "a possessive quantifier",
                "the greedy quantifier, without the '+'",
            )
        if char == "*" or (char == "{" and self._brace_shape(position) is not None):
            self._refuse(
                position,
                "a quantifier on a quantifier",
                "one quantifier, or a group (?:...) around the repeated part",
            )
