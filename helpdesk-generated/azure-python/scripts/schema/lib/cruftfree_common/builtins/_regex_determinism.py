"""The determinism check of the regex pattern language."""

from __future__ import annotations

from typing import NoReturn

from cruftfree_common.builtins._regex_nodes import (
    _ALTERNATIVES_MEET_REWRITE,
    _BODY_MEETS_FOLLOW_REWRITE,
    _EMPTY_BODY,
    _EMPTY_BODY_REWRITE,
    _NO_CODE_POINTS,
    Alternation,
    Group,
    RegexNode,
    RegexPatternError,
    Repeat,
    Sequence,
    _is_varying,
    _named_code_points,
    _StartSets,
)
from cruftfree_common.builtins.regex_code_points import (
    CodePointRanges,
    code_point_ranges_intersection,
    code_point_ranges_union,
)


class _DeterminismCheck:
    """Refuse the first repetition or alternation of a read tree that is not deterministic.

    The tree is walked from the root with what can follow each node: the code points
    that can start the rest of the pattern after it, the next pass of every repetition
    around it included. A repetition whose count varies needs a body that cannot match
    the empty string and that shares no starting code point with what follows it; an
    alternation inside any repetition but ``{1}`` needs alternatives with disjoint starts.
    """

    def __init__(self, pattern: str) -> None:
        self._pattern = pattern
        self._start_sets = _StartSets()

    def check(self, root: RegexNode) -> None:
        self._walk(root, _NO_CODE_POINTS, inside_repetition=False)

    def _refuse(self, node: RegexNode, construct: str, supported: str) -> NoReturn:
        raise RegexPatternError(self._pattern, node.span[0], construct, supported)

    def _starts_with_follow(
        self, node: RegexNode, follow: CodePointRanges
    ) -> CodePointRanges:
        """The code points that start the input at *node*.

        Its own, and *follow* too when it can match the empty string.
        """
        nullable, first = self._start_sets.start(node)
        return code_point_ranges_union(first, follow) if nullable else first

    # -- the walk ------------------------------------------------------------

    def _walk(
        self, node: RegexNode, follow: CodePointRanges, inside_repetition: bool
    ) -> None:
        if isinstance(node, Group):
            self._walk(node.body, follow, inside_repetition)
        elif isinstance(node, Repeat):
            self._walk_repeat(node, follow, inside_repetition)
        elif isinstance(node, Alternation):
            if inside_repetition:
                self._check_alternatives_disjoint(node, follow)
            for alternative in node.alternatives:
                self._walk(alternative, follow, inside_repetition)
        elif isinstance(node, Sequence):
            self._walk_sequence(node, follow, inside_repetition)

    def _walk_sequence(
        self, node: Sequence, follow: CodePointRanges, inside_repetition: bool
    ) -> None:
        follows: list[CodePointRanges] = []
        after = follow
        for item in reversed(node.items):
            follows.append(after)
            after = self._starts_with_follow(item, after)
        for item, item_follow in zip(node.items, reversed(follows), strict=True):
            self._walk(item, item_follow, inside_repetition)

    def _walk_repeat(
        self, node: Repeat, follow: CodePointRanges, inside_repetition: bool
    ) -> None:
        nullable, first = self._start_sets.start(node.body)
        varying = _is_varying(node)
        if varying:
            if nullable:
                self._refuse(node, _EMPTY_BODY, _EMPTY_BODY_REWRITE)
            overlap = code_point_ranges_intersection(first, follow)
            if overlap:
                self._refuse(
                    node,
                    "a varying repetition whose body and what follows it can both start "
                    f"with {_named_code_points(overlap)}",
                    _BODY_MEETS_FOLLOW_REWRITE,
                )
        passes_again = node.high is None or node.high > 1
        body_follow = code_point_ranges_union(first, follow) if passes_again else follow
        # A fixed count of passes multiplies an ambiguous alternation's choices per
        # pass, as a varying count does: only ``{1}`` leaves its alternations free.
        self._walk(node.body, body_follow, inside_repetition or varying or passes_again)

    def _check_alternatives_disjoint(
        self, node: Alternation, follow: CodePointRanges
    ) -> None:
        seen = _NO_CODE_POINTS
        for alternative in node.alternatives:
            starts = self._starts_with_follow(alternative, follow)
            overlap = code_point_ranges_intersection(starts, seen)
            if overlap:
                self._refuse(
                    node,
                    "an alternation inside a repetition whose alternatives can "
                    f"both start with {_named_code_points(overlap)}",
                    _ALTERNATIVES_MEET_REWRITE,
                )
            seen = code_point_ranges_union(seen, starts)
