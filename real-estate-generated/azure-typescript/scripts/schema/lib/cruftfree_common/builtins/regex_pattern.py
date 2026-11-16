"""The regex pattern language, read once into one tree for every target.

:func:`read_regex_pattern` reads a pattern (the string after ``.cfree`` decoding)
left to right and refuses, at the first construct outside the language, with a
:class:`RegexPatternError`. Matching is case-sensitive, over code points:

- a code point that is not syntax, or ``\\`` before one of the 32 ASCII
  punctuation characters, is that code point; ``\\uHHHH`` (exactly four hex
  digits, not U+0000, not a surrogate) is U+HHHH; ``\\n \\t \\r`` are U+000A,
  U+0009, U+000D;
- ``.`` is every code point but U+000A; ``[...]`` / ``[^...]`` is a set or its
  complement, with ranges by code point; ``\\d \\w \\s`` and their complements
  ``\\D \\W \\S`` are the fixed sets of :mod:`~cruftfree_common.builtins.regex_code_points`;
- ``(...)``, ``(?:...)``, ``(?<name>...)`` are a capturing, non-capturing and
  named group, numbered by opening parenthesis among the capturing groups (at
  most nine; a name is an ASCII letter then letters, digits, ``_``, unique);
  ``|`` is alternation;
- ``* + ? {n} {n,} {n,m}`` are greedy, with bounds decimal, no leading zero, at
  most 255, ``n`` at most ``m`` and an upper count of at least 1;
- ``^`` and ``$`` are the start and end of the whole input, written only at the
  start and end of a top-level alternative.

Syntax characters are literal only escaped: outside a set ``\\ ^ $ . | ? * + ( )
[ ] { }``, inside one ``] \\ - ^ [`` (at its edges too). Every other escape,
backreferences, lookaround, word boundaries, lazy, possessive and atomic forms,
inline flags, property and POSIX classes, U+0000, surrogates, the empty pattern,
an empty alternative or group, a set matching nothing, a quantifier on nothing or
on another, and a tenth capturing group are refused.

Repetition and alternation are deterministic, so a backtracking engine has one way
to continue at each code point and a match attempt from one starting position
takes time linear in the input. A repetition whose count varies (``* + ?``,
``{n,}``, ``{n,m}`` with ``n < m``) has a body that cannot match the empty string,
and no code point starts both its body and what follows it (the body's next pass
included). The alternatives of an alternation inside any repetition but ``{1}``,
a fixed count included, start with disjoint code points (an alternative that can
match the empty string starts with what follows the alternation too): a fixed
count multiplies an ambiguous alternation's choices once per pass, so
``(?:a|aa){255}`` would backtrack through every composition of its passes.
``(a+)+``, ``\\d+\\d+``, ``(a|ab)*``, ``(?:a|ab){2}`` and ``foo.*bar`` are refused,
naming the overlapping code points; an alternation outside every repetition is
tried once per position it starts at, and is not restricted.

Every regex operation is one of two kinds. A whole-value operation
(``String.matches``, ``Regex.matches``, ``Validator.matches``, the scalar
``pattern`` constraint) holds when the pattern matches the whole value, and reads
its pattern with :func:`read_regex_pattern`. A found operation
(:data:`FOUND_REGEX_OPERATIONS`: ``Regex.findAll``, ``String.replaceRegex``,
``Regex.replace``) acts on every non-overlapping match, left to right, each the
match a leftmost-first engine finds at the leftmost position it can start
(quantifiers greedy, alternatives tried in order), each search starting where the
previous match ended; ``Regex.findAll`` returns each match's whole text. It reads
its pattern with :func:`read_found_regex_pattern`, which also refuses a pattern
that can match the empty string (an anchor counting as empty: ``\\d*``, ``$``,
``a?$``), and one whose search over many starting positions is not linear in the
input: a varying repetition holding a code point that begins a match, that the
match cannot end right after (``a*b``, ``[a-z]+@``, ``(\\d+,)+``, ``\\d+$``), while
``\\d+``, ``\\d+(\\.\\d+)?``, ``ab*c``, ``\\$\\d+`` and ``^\\d+x`` are read.

The tree is frozen nodes; each node carries ``span``, the code-point offsets
``[start, end)`` in the pattern it was read from.

- :class:`CodePointSet` is every single-code-point construct (a literal, an escape,
  ``.``, a bracket set, a class escape) as one shape: its ranges, a complement
  already applied;
- :class:`Sequence` is a concatenation and :class:`Alternation` a ``|`` choice, each
  of two or more parts;
- :class:`Group` is a capturing group, numbered by its opening parenthesis among the
  capturing groups (named ones included); a non-capturing group is its body;
- :class:`Repeat` is a greedy quantifier with its bounds (``high`` ``None`` for no
  upper bound);
- :class:`Anchor` is ``^`` or ``$``, the start or end of the whole input.

:class:`RegexPatternError` is a pattern outside the language: the 0-based
code-point ``position`` of the offending construct, the ``construct`` it is and
the ``supported`` form to write instead; its message prints the position 1-based.

A target renders the tree with :mod:`cruftfree_common.builtins.regex_rendering`, one
walk given its engine's spelling row, never the pattern text.

# @canonical(builtins/regex-pattern): The one regex pattern language every regex argument is read in, and its tree
# @rule: Every regex argument is read with read_regex_pattern, a found operation's with read_found_regex_pattern; a target renders the tree, never the pattern text
# @anti-pattern: Passing a DSL pattern to a host regex engine as written
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from cruftfree_common.builtins._regex_nodes import (
    _NO_CODE_POINTS,
    FOUND_REGEX_OPERATIONS,
    Alternation,
    Anchor,
    CodePointSet,
    Group,
    RegexNode,
    RegexPattern,
    RegexPatternError,
    Repeat,
    Sequence,
    _is_varying,
    _named_code_points,
    _StartSets,
)
from cruftfree_common.builtins._regex_reader import _PatternReader
from cruftfree_common.builtins.regex_code_points import (
    CodePointRanges,
    code_point_ranges_intersection,
    code_point_ranges_union,
)

__all__ = [
    "read_found_regex_pattern",
    "read_regex_pattern",
]


_FOUND_NONEMPTY_REWRITE: Final[str] = (
    "a pattern whose every match holds at least one code point, such as \\d+ for \\d*"
)
_FOUND_BOUNDED_REWRITE: Final[str] = (
    "a repetition holding no code point that begins a match, such as \\$\\d+, "
    "or one the match can end right after, such as \\d+(\\.\\d+)?"
)


def _held_code_points(node: RegexNode) -> CodePointRanges:
    """Every code point of every set inside *node*, at any depth."""
    if isinstance(node, CodePointSet):
        return node.ranges
    if isinstance(node, Anchor):
        return _NO_CODE_POINTS
    if isinstance(node, Group | Repeat):
        return _held_code_points(node.body)
    parts = node.alternatives if isinstance(node, Alternation) else node.items
    return code_point_ranges_union(*(_held_code_points(part) for part in parts))


def _holds_end_anchor(node: RegexNode) -> bool:
    """Whether *node* holds a ``$`` at any depth."""
    if isinstance(node, Anchor):
        return node.edge == "end"
    if isinstance(node, CodePointSet):
        return False
    if isinstance(node, Group | Repeat):
        return _holds_end_anchor(node.body)
    parts = node.alternatives if isinstance(node, Alternation) else node.items
    return any(_holds_end_anchor(part) for part in parts)


def _begins_with_start_anchor(alternative: RegexNode) -> bool:
    """Whether the top-level *alternative* begins with ``^``, so it matches only at the input's start."""
    first = alternative.items[0] if isinstance(alternative, Sequence) else alternative
    return isinstance(first, Anchor) and first.edge == "start"


@dataclass(frozen=True)
class _PositionFacts:
    """What one node contributes to the position automaton of a read tree.

    A position is one set of the tree (a leaf); a run of the automaton is at the
    position whose set read the last code point.

    Attributes:
        nullable: The node can match the empty string, an anchor counting as empty.
        passes_clean: The node can be passed without consuming a code point or
            checking ``$``.
        first: The positions the node can begin with.
        last: The positions the node can end with.
        ends_clean: The positions after which the whole match can end, wherever the
            node stands, without consuming a code point or checking ``$``.
    """

    nullable: bool
    passes_clean: bool
    first: frozenset[int]
    last: frozenset[int]
    ends_clean: frozenset[int]


_NO_POSITIONS: Final[frozenset[int]] = frozenset()
_ON_PATH: Final[int] = 1
_EXPLORED: Final[int] = 2


class _AttemptOverlap:
    """Whether two attempts of one search can read a stretch of unbounded length together.

    A found operation's search attempts a match at a position and, when the attempt
    fails, at the next one; when it matches, at the match's end. A later attempt is
    therefore only made while every earlier one has failed, or has matched no further
    than where the later one starts. Every attempt follows the position automaton of
    the tree (its first, last and follow sets); a repetition that can pass more than
    once is a loop whatever its bounds, so the automaton admits every path an attempt
    takes. The search is linear in the input when no two attempts read more than a
    pattern-bounded stretch together: then every code point is read by a bounded
    number of attempts.

    Two attempts reading together are a pair of positions stepping on one code point,
    from the earlier attempt at any position it reaches and the later one at the start
    of a top-level alternative not beginning with ``^``. The earlier attempt never
    steps to a position the whole match can end after: the attempt would match past
    the later start, which is then never attempted. A loop of such pairs is a stretch
    of any length both read; with none, every stretch is shorter than the pair count.
    """

    def __init__(self, root: RegexNode) -> None:
        self._sets: list[CodePointRanges] = []
        self._follow: list[set[int]] = []
        self._meets: dict[tuple[int, int], bool] = {}
        alternatives = root.alternatives if isinstance(root, Alternation) else (root,)
        facts = [(alternative, self._facts(alternative)) for alternative in alternatives]
        self._first = frozenset().union(*(fact.first for _, fact in facts))
        self._restart_first = frozenset().union(
            *(
                fact.first
                for alternative, fact in facts
                if not _begins_with_start_anchor(alternative)
            )
        )
        self._match_ends = frozenset().union(*(fact.ends_clean for _, fact in facts))

    def unbounded(self) -> bool:
        """Whether an earlier attempt not yet matched and a later one can read any length together."""
        explored: dict[tuple[int, int], int] = {}
        return any(
            self._loops_from(start, explored)
            for start in self._starting_pairs()
            if start not in explored
        )

    def _facts(self, node: RegexNode) -> _PositionFacts:
        if isinstance(node, CodePointSet):
            self._sets.append(node.ranges)
            self._follow.append(set())
            only = frozenset({len(self._sets) - 1})
            return _PositionFacts(False, False, only, only, only)
        if isinstance(node, Anchor):
            return _PositionFacts(
                True, node.edge == "start", _NO_POSITIONS, _NO_POSITIONS, _NO_POSITIONS
            )
        if isinstance(node, Group):
            return self._facts(node.body)
        if isinstance(node, Repeat):
            return self._repeat_facts(node)
        if isinstance(node, Alternation):
            parts = [self._facts(alternative) for alternative in node.alternatives]
            return _PositionFacts(
                any(part.nullable for part in parts),
                any(part.passes_clean for part in parts),
                frozenset().union(*(part.first for part in parts)),
                frozenset().union(*(part.last for part in parts)),
                frozenset().union(*(part.ends_clean for part in parts)),
            )
        return self._sequence_facts(node)

    def _repeat_facts(self, node: Repeat) -> _PositionFacts:
        """A repetition that can pass more than once loops from its last positions to its
        first; it ends the match cleanly only when one pass satisfies its count."""
        body = self._facts(node.body)
        if node.high is None or node.high > 1:
            for position in body.last:
                self._follow[position] |= body.first
        return _PositionFacts(
            body.nullable or node.low == 0,
            body.passes_clean or node.low == 0,
            body.first,
            body.last,
            body.ends_clean if node.low <= 1 else _NO_POSITIONS,
        )

    def _sequence_facts(self, node: Sequence) -> _PositionFacts:
        parts = [self._facts(item) for item in node.items]
        for index, part in enumerate(parts):
            following = _first_through(parts[index + 1 :])
            for position in part.last:
                self._follow[position] |= following
        last: set[int] = set()
        ends_clean: set[int] = set()
        rest_nullable = True
        rest_passes_clean = True
        for part in reversed(parts):
            if rest_nullable:
                last |= part.last
            if rest_passes_clean:
                ends_clean |= part.ends_clean
            rest_nullable = rest_nullable and part.nullable
            rest_passes_clean = rest_passes_clean and part.passes_clean
        return _PositionFacts(
            rest_nullable,
            rest_passes_clean,
            _first_through(parts),
            frozenset(last),
            frozenset(ends_clean),
        )

    def _steps_together(self, earlier: int, later: int) -> bool:
        """Whether both attempts can step to these positions on one code point, the
        earlier one still unmatched."""
        if earlier in self._match_ends:
            return False
        key = (earlier, later)
        if key not in self._meets:
            self._meets[key] = bool(
                code_point_ranges_intersection(self._sets[earlier], self._sets[later])
            )
        return self._meets[key]

    def _reachable(self) -> set[int]:
        reached = set(self._first)
        pending = list(self._first)
        while pending:
            for following in self._follow[pending.pop()]:
                if following not in reached:
                    reached.add(following)
                    pending.append(following)
        return reached

    def _starting_pairs(self) -> set[tuple[int, int]]:
        """The pairs after the later attempt's first code point, the earlier attempt at any
        position it reaches."""
        return {
            (earlier, later)
            for reached in self._reachable()
            for earlier in self._follow[reached]
            for later in self._restart_first
            if self._steps_together(earlier, later)
        }

    def _successors(self, pair: tuple[int, int]) -> list[tuple[int, int]]:
        earlier, later = pair
        return [
            (next_earlier, next_later)
            for next_earlier in self._follow[earlier]
            for next_later in self._follow[later]
            if self._steps_together(next_earlier, next_later)
        ]

    def _loops_from(
        self, start: tuple[int, int], explored: dict[tuple[int, int], int]
    ) -> bool:
        """Whether a loop of pairs is reachable from *start*: a depth-first walk that
        meets a pair still on its path."""
        explored[start] = _ON_PATH
        path = [(start, iter(self._successors(start)))]
        while path:
            pair, successors = path[-1]
            following = next(
                (step for step in successors if explored.get(step) != _EXPLORED), None
            )
            if following is None:
                explored[pair] = _EXPLORED
                path.pop()
            elif explored.get(following) == _ON_PATH:
                return True
            else:
                explored[following] = _ON_PATH
                path.append((following, iter(self._successors(following))))
        return False


def _first_through(parts: list[_PositionFacts]) -> frozenset[int]:
    """The positions a run of *parts* can begin with: each part's first up to the first
    part that cannot match the empty string."""
    first: set[int] = set()
    for part in parts:
        first |= part.first
        if not part.nullable:
            break
    return frozenset(first)


class _FoundSearchCheck:
    """Refuse a pattern a found operation cannot search in time linear in the input.

    A found operation attempts a match at each position in turn, so it needs two
    things the reader does not ask. No match may be empty: the root cannot match the
    empty string, an anchor counting as empty. And no failed attempt may consume a run
    a later attempt restarts in and reads as far: the restart set is the start of
    every top-level alternative not beginning with ``^``, and a varying repetition
    holding a code point of it (in any set of its body) must be one the match can end
    right after, without consuming a code point or checking ``$``. The walk carries,
    from the root down, whether the match can end right after each node; a repetition
    passes it to its body when its count needs at most one pass, or when its body can
    match the empty string and holds no ``$``, since otherwise another required pass
    follows. A repetition that fails this first test is refused only when the second
    holds too: an earlier attempt not yet matched and a later one can read a stretch
    of any length together (:class:`_AttemptOverlap`). A later attempt restarting in
    the run then dies within a pattern-bounded number of code points, or leaves it.
    """

    def __init__(self, pattern: str, operation: str, root: RegexNode) -> None:
        self._pattern = pattern
        self._operation = operation
        self._root = root
        self._start_sets = _StartSets()
        self._restart: CodePointRanges = _NO_CODE_POINTS
        self._overlap_unbounded: bool | None = None

    def check(self) -> None:
        root = self._root
        nullable, _ = self._start_sets.start(root)
        if nullable:
            raise RegexPatternError(
                self._pattern,
                0,
                f"a pattern that can match the empty string, passed to {self._operation}",
                _FOUND_NONEMPTY_REWRITE,
            )
        alternatives = root.alternatives if isinstance(root, Alternation) else (root,)
        self._restart = code_point_ranges_union(
            *(
                self._start_sets.start(alternative)[1]
                for alternative in alternatives
                if not _begins_with_start_anchor(alternative)
            )
        )
        if self._restart:
            self._walk(root, ends_clean=True)

    def _attempts_overlap_unbounded(self) -> bool:
        """The second test of a repetition the restart set flags, worked out once."""
        if self._overlap_unbounded is None:
            self._overlap_unbounded = _AttemptOverlap(self._root).unbounded()
        return self._overlap_unbounded

    def _can_end_through(self, node: RegexNode) -> bool:
        """Whether the match can pass *node* without consuming a code point or checking ``$``."""
        nullable, _ = self._start_sets.start(node)
        return nullable and not _holds_end_anchor(node)

    def _walk(self, node: RegexNode, ends_clean: bool) -> None:
        if isinstance(node, Group):
            self._walk(node.body, ends_clean)
        elif isinstance(node, Alternation):
            for alternative in node.alternatives:
                self._walk(alternative, ends_clean)
        elif isinstance(node, Sequence):
            for index, item in enumerate(node.items):
                rest_passes = all(
                    self._can_end_through(after) for after in node.items[index + 1 :]
                )
                self._walk(item, ends_clean and rest_passes)
        elif isinstance(node, Repeat):
            self._walk_repeat(node, ends_clean)

    def _walk_repeat(self, node: Repeat, ends_clean: bool) -> None:
        if _is_varying(node) and not ends_clean:
            overlap = code_point_ranges_intersection(
                _held_code_points(node.body), self._restart
            )
            if overlap and self._attempts_overlap_unbounded():
                raise RegexPatternError(
                    self._pattern,
                    node.span[0],
                    f"a varying repetition holding {_named_code_points(overlap)}, which "
                    "can begin a match, that the match cannot end right after, passed "
                    f"to {self._operation}",
                    _FOUND_BOUNDED_REWRITE,
                )
        passes_on = node.low <= 1 or self._can_end_through(node.body)
        self._walk(node.body, ends_clean and passes_on)


def read_regex_pattern(pattern: str) -> RegexPattern:
    """Read *pattern* (the string after ``.cfree`` decoding) into its tree.

    Raises:
        RegexPatternError: the pattern holds a construct outside the regex pattern
            language, or a repetition or alternation that is not deterministic, named
            with its position and the supported form to write.
    """
    return _PatternReader(pattern).read()


def read_found_regex_pattern(pattern: str, operation: str) -> RegexPattern:
    """Read *pattern* for the found operation *operation* (``Category.member``).

    A found operation acts on every non-overlapping match, left to right, so beyond
    what :func:`read_regex_pattern` asks the pattern can match no empty string and
    its search is bounded linearly in the input (:class:`_FoundSearchCheck`).

    Raises:
        ValueError: *operation* is not one of :data:`FOUND_REGEX_OPERATIONS`.
        RegexPatternError: the pattern is outside the language, can match the empty
            string, or holds a repetition a failed attempt can consume while a later
            attempt restarts in it; named with the operation, the position and the
            supported form to write.
    """
    if operation not in FOUND_REGEX_OPERATIONS:
        raise ValueError(
            f"{operation!r} is not a found regex operation; it is one of "
            f"{sorted(FOUND_REGEX_OPERATIONS)}, or a whole-value one read with read_regex_pattern"
        )
    read = read_regex_pattern(pattern)
    _FoundSearchCheck(pattern, operation, read.root).check()
    return read
