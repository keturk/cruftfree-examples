"""One walk rendering a read regex tree for any engine, given that engine's spelling row.

A pattern argument is read once into its tree
(:mod:`cruftfree_common.builtins.regex_pattern`); every target writes that tree in its
engine's syntax, never the author's text. Engines differ only in how they spell a
few parts, so each renderer is :func:`render_regex_pattern` with a
:class:`RegexSpelling` row: the syntax escaped outside and inside a set, the
code-point escape, the two anchors of the whole input and the named-group head.
Everything else is shared: explicit bracket sets (no shorthand class, no ``.``),
printable ASCII standing as itself, one grouping rule and one quantifier spelling.

:func:`render_ecmascript_pattern` is the walk in :data:`ECMASCRIPT_SPELLING`, the
dialect of JSON Schema patterns and of every ECMAScript-dialect engine: explicit
sets, escaped syntax, ``\\u{H...}`` outside printable ASCII, a whole value wrapped
as ``^(?:...)$``.

# @canonical(builtins/regex-rendering): The one walk rendering a read regex tree for any engine, given that engine's RegexSpelling row
# @canonical(builtins/regex-ecmascript-rendering): The one ECMAScript (u mode) rendering of a read regex tree, for every ECMAScript-dialect consumer and every published pattern
# @rule: A renderer is render_regex_pattern with its engine's RegexSpelling row, never a walk of its own
# @anti-pattern: A per-engine copy of the quantifier spelling or the precedence-grouping walk
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from cruftfree_common.builtins._regex_nodes import (
    Alternation,
    CodePointSet,
    Group,
    RegexNode,
    RegexPattern,
    Repeat,
    Sequence,
)

__all__ = [
    "ECMASCRIPT_SPELLING",
    "RegexSpelling",
    "hex_code_point_escape",
    "render_ecmascript_pattern",
    "render_regex_pattern",
]

_FIRST_PRINTABLE_ASCII: Final[int] = 0x20
_LAST_PRINTABLE_ASCII: Final[int] = 0x7E
_LAST_BMP_CODE_POINT: Final[int] = 0xFFFF
_QUANTIFIER_SHORTHANDS: Final[Mapping[tuple[int, int | None], str]] = MappingProxyType(
    {(0, None): "*", (1, None): "+", (0, 1): "?"}
)


@dataclass(frozen=True)
class RegexSpelling:
    """How one regex engine spells the parts of a read tree engines write differently.

    The rest of a rendering is one walk (:func:`render_regex_pattern`): every set is
    a bracket set of its ranges (no shorthand class, no ``.``) and a single code point
    an atom; printable ASCII (U+0020-U+007E) stands as itself, ``\\``-escaped where it
    is syntax; an alternation inside a sequence, and a repeated part that is neither
    a set nor a group, are wrapped in ``(?:...)``; a quantifier is ``*``, ``+``,
    ``?`` or its braces; and a whole value is wrapped in the two anchors around
    ``(?:...)``.

    Attributes:
        syntax: The characters the engine reads as syntax outside a set.
        set_syntax: The characters escaped inside a set.
        code_point_escape: A code point outside printable ASCII as the engine's escape.
        start_anchor: The start of the whole input, which no flag moves.
        end_anchor: The end of the whole input, which matches before nothing else.
        named_group_head: The opening of a named group, given its name (a plain
            ``(`` on an engine without named groups: groups are numbered alike).
    """

    syntax: frozenset[str]
    set_syntax: frozenset[str]
    code_point_escape: Callable[[int], str]
    start_anchor: str
    end_anchor: str
    named_group_head: Callable[[str], str]


def hex_code_point_escape(code_point: int) -> str:
    """``\\uHHHH`` for a BMP code point, ``\\UHHHHHHHH`` above U+FFFF."""
    if code_point <= _LAST_BMP_CODE_POINT:
        return f"\\u{code_point:04X}"
    return f"\\U{code_point:08X}"


def _spelled_code_point(
    code_point: int, syntax: frozenset[str], spelling: RegexSpelling
) -> str:
    """*code_point* as *spelling* writes it, the characters of *syntax* escaped."""
    if not _FIRST_PRINTABLE_ASCII <= code_point <= _LAST_PRINTABLE_ASCII:
        return spelling.code_point_escape(code_point)
    char = chr(code_point)
    return f"\\{char}" if char in syntax else char


def _spelled_set(node: CodePointSet, spelling: RegexSpelling) -> str:
    """One code point as an atom; several as a bracket set of their ranges."""
    (first_low, first_high), *rest = node.ranges
    if not rest and first_low == first_high:
        return _spelled_code_point(first_low, spelling.syntax, spelling)
    members = "".join(
        _spelled_code_point(low, spelling.set_syntax, spelling)
        if low == high
        else f"{_spelled_code_point(low, spelling.set_syntax, spelling)}-"
        f"{_spelled_code_point(high, spelling.set_syntax, spelling)}"
        for low, high in node.ranges
    )
    return f"[{members}]"


def _quantifier(low: int, high: int | None) -> str:
    shorthand = _QUANTIFIER_SHORTHANDS.get((low, high))
    if shorthand is not None:
        return shorthand
    if high is None:
        return f"{{{low},}}"
    return f"{{{low}}}" if low == high else f"{{{low},{high}}}"


def _spelled_node(node: RegexNode, spelling: RegexSpelling) -> str:
    """*node* as *spelling* writes it, grouped wherever precedence needs it."""
    if isinstance(node, CodePointSet):
        return _spelled_set(node, spelling)
    if isinstance(node, Sequence):
        return "".join(
            f"(?:{_spelled_node(item, spelling)})"
            if isinstance(item, Alternation)
            else _spelled_node(item, spelling)
            for item in node.items
        )
    if isinstance(node, Alternation):
        return "|".join(_spelled_node(item, spelling) for item in node.alternatives)
    if isinstance(node, Group):
        head = "(" if node.name is None else spelling.named_group_head(node.name)
        return f"{head}{_spelled_node(node.body, spelling)})"
    if isinstance(node, Repeat):
        body = _spelled_node(node.body, spelling)
        if not isinstance(node.body, CodePointSet | Group):
            body = f"(?:{body})"
        return f"{body}{_quantifier(node.low, node.high)}"
    return spelling.start_anchor if node.edge == "start" else spelling.end_anchor


def render_regex_pattern(
    tree: RegexPattern, spelling: RegexSpelling, *, whole_value: bool
) -> str:
    """*tree* as the pattern source of the engine *spelling* describes.

    Args:
        tree: The read pattern (``read_regex_pattern`` / ``read_found_regex_pattern``).
        spelling: The engine's row.
        whole_value: Wrap the source as ``<start>(?:...)<end>``, so a search for it is
            the whole-value match; ``False`` for a found operation.
    """
    source = _spelled_node(tree.root, spelling)
    if not whole_value:
        return source
    return f"{spelling.start_anchor}(?:{source}){spelling.end_anchor}"


def _ecmascript_code_point_escape(code_point: int) -> str:
    return f"\\u{{{code_point:X}}}"


def _ecmascript_named_group_head(name: str) -> str:
    return f"(?<{name}>"


#: ECMAScript's Unicode (``u``) mode: ``\\u{H...}`` outside printable ASCII, ``^``
#: and ``$`` the edges of the whole input (no ``m`` flag), ``(?<name>...)``.
ECMASCRIPT_SPELLING: Final[RegexSpelling] = RegexSpelling(
    syntax=frozenset("^$\\.*+?()[]{}|"),
    set_syntax=frozenset("\\][^-"),
    code_point_escape=_ecmascript_code_point_escape,
    start_anchor="^",
    end_anchor="$",
    named_group_head=_ecmascript_named_group_head,
)


def render_ecmascript_pattern(tree: RegexPattern, *, whole_value: bool) -> str:
    """*tree* as the source of an ECMAScript regular expression in Unicode (``u``) mode.

    The shared rendering (:func:`render_regex_pattern`) in
    :data:`ECMASCRIPT_SPELLING`. With *whole_value* the pattern is wrapped as
    ``^(?:...)$``, so an unanchored test of it is the whole-value match. The source is
    text a consumer quotes for its own language and compiles with the ``u`` flag
    (``gu`` for a found operation).
    """
    return render_regex_pattern(tree, ECMASCRIPT_SPELLING, whole_value=whole_value)
