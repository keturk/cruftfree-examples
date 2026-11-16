"""The code points a reader of a source file cannot see.

Author text reaches generated string literals, and a code point that renders as
nothing -- a control, a zero-width character, a bidi control (Trojan Source,
CVE-2021-42574), a non-ASCII space -- makes the source a reviewer reads differ
from the source a compiler reads. What counts as "cannot see" is decided here,
once: every escaper of every target and every validator over framework sources
reads this predicate, so no escaper misses a code point another catches.

A code point is hidden in source when any of these holds:

- it is not printable (``str.isprintable``): Cc (C0, DEL, C1), Cf (bidi
  controls, U+200B..U+200F, U+FEFF, tags), Zs other than U+0020, Zl, Zp, Cs,
  Co and Cn;
- it is a Default_Ignorable_Code_Point (:data:`DEFAULT_IGNORABLE_RANGES`), which
  adds the printable combining marks and letters that render as nothing
  (U+034F, the Hangul fillers, the Khmer inherent vowels, the Mongolian free
  variation selectors, the variation selectors);
- it is U+2800 BRAILLE PATTERN BLANK, a glyph with no ink.

``str.isprintable`` reads the running interpreter's Unicode database. A code
point an older database leaves unassigned is Cn there, so it is hidden there:
on every supported version no hidden code point is emitted raw, and two
versions differ only on a code point the newer one assigns as a visible
character (the older escapes it; both literals decode to the same value).

A comment has no escape grammar, so a literal's ``\\uHHHH`` would be read there
as six characters of prose. :func:`visible_text` writes each flagged code point
as the visible text ``[U+HHHH]`` instead, the one spelling every comment,
docstring and catalog comment writer uses.

A string literal does have an escape grammar. A language's literal escaper
handles its own delimiters and short escapes first, then hands the result to
:func:`escape_hidden` with the form its grammar decodes. The forms are named by
spelling, never by language: a new language's escaper picks the form its
grammar reads.

=========================  ===============================================  =====================
Form                       Spelling                                         Grammars
=========================  ===============================================  =====================
``UTF16_UNITS``            ``\\uhhhh``; an astral code point as two UTF-16  TypeScript/JavaScript,
                           units (a surrogate pair)                         JSON
``SIZED``                  ``\\xhh``, ``\\uhhhh``, ``\\Uhhhhhhhh`` by size,  Python
                           exactly as ``repr`` writes them
``BRACED``                 ``\\u{h…}``, the code point's digits with no      Bicep, Dart
                           leading zeros
``CHARACTER_REFERENCE``    ``&#xh…;``, the code point's digits with no      XML, and markup that
                           leading zeros                                    reads XML's references
                                                                            (Angular templates)
``PLIST_UNITS``            ``\\Uhhhh`` per UTF-16 unit; an astral code      Apple old-style
                           point as two units (a surrogate pair)            property lists
``FOUR_OR_PLUS_SIX``       ``\\hhhh``, exactly four digits; a code point     SQL Unicode-escape
                           above U+FFFF as ``\\+hhhhhh``, exactly six       string constants
                                                                            (``U&'…'``)
``FOUR_OR_EIGHT``          ``\\uhhhh``; a code point above U+FFFF as        TOML basic strings
                           ``\\Uhhhhhhhh``, exactly eight digits
=========================  ===============================================  =====================

Hex digits are lowercase in every form, as ``repr`` and ``json.dumps`` write them.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Final

#: The Unicode version :data:`DEFAULT_IGNORABLE_RANGES` is copied from
#: (``DerivedCoreProperties.txt``).
DEFAULT_IGNORABLE_UNICODE_VERSION: Final[str] = "16.0.0"

#: The Default_Ignorable_Code_Point property: each ``(first, last)`` inclusive
#: range as ``DerivedCoreProperties.txt`` of :data:`DEFAULT_IGNORABLE_UNICODE_VERSION`
#: lists it, in its order (27 ranges, 4,174 code points).
DEFAULT_IGNORABLE_RANGES: Final[tuple[tuple[int, int], ...]] = (
    (0x00AD, 0x00AD),  # Cf SOFT HYPHEN
    (0x034F, 0x034F),  # Mn COMBINING GRAPHEME JOINER
    (0x061C, 0x061C),  # Cf ARABIC LETTER MARK
    (0x115F, 0x1160),  # Lo HANGUL CHOSEONG FILLER..HANGUL JUNGSEONG FILLER
    (0x17B4, 0x17B5),  # Mn KHMER VOWEL INHERENT AQ..KHMER VOWEL INHERENT AA
    (0x180B, 0x180D),  # Mn MONGOLIAN FREE VARIATION SELECTOR ONE..THREE
    (0x180E, 0x180E),  # Cf MONGOLIAN VOWEL SEPARATOR
    (0x180F, 0x180F),  # Mn MONGOLIAN FREE VARIATION SELECTOR FOUR
    (0x200B, 0x200F),  # Cf ZERO WIDTH SPACE..RIGHT-TO-LEFT MARK
    (0x202A, 0x202E),  # Cf LEFT-TO-RIGHT EMBEDDING..RIGHT-TO-LEFT OVERRIDE
    (0x2060, 0x2064),  # Cf WORD JOINER..INVISIBLE PLUS
    (0x2065, 0x2065),  # Cn <reserved-2065>
    (0x2066, 0x206F),  # Cf LEFT-TO-RIGHT ISOLATE..NOMINAL DIGIT SHAPES
    (0x3164, 0x3164),  # Lo HANGUL FILLER
    (0xFE00, 0xFE0F),  # Mn VARIATION SELECTOR-1..VARIATION SELECTOR-16
    (0xFEFF, 0xFEFF),  # Cf ZERO WIDTH NO-BREAK SPACE
    (0xFFA0, 0xFFA0),  # Lo HALFWIDTH HANGUL FILLER
    (0xFFF0, 0xFFF8),  # Cn <reserved-FFF0>..<reserved-FFF8>
    (0x1BCA0, 0x1BCA3),  # Cf SHORTHAND FORMAT LETTER OVERLAP..SHORTHAND FORMAT UP STEP
    (0x1D173, 0x1D17A),  # Cf MUSICAL SYMBOL BEGIN BEAM..MUSICAL SYMBOL END PHRASE
    (0xE0000, 0xE0000),  # Cn <reserved-E0000>
    (0xE0001, 0xE0001),  # Cf LANGUAGE TAG
    (0xE0002, 0xE001F),  # Cn <reserved-E0002>..<reserved-E001F>
    (0xE0020, 0xE007F),  # Cf TAG SPACE..CANCEL TAG
    (0xE0080, 0xE00FF),  # Cn <reserved-E0080>..<reserved-E00FF>
    (0xE0100, 0xE01EF),  # Mn VARIATION SELECTOR-17..VARIATION SELECTOR-256
    (0xE01F0, 0xE0FFF),  # Cn <reserved-E01F0>..<reserved-E0FFF>
)

#: U+2800 BRAILLE PATTERN BLANK: printable (So) and not ignorable, but it has no ink.
BRAILLE_PATTERN_BLANK: Final[int] = 0x2800

_DEFAULT_IGNORABLE: Final[frozenset[int]] = frozenset(
    code_point
    for first, last in DEFAULT_IGNORABLE_RANGES
    for code_point in range(first, last + 1)
)


# @canonical(text/hidden-code-point): Whether a code point is one a reader of source cannot see
# @rule: Every escaper of author text into a generated literal, and every check over sources, reads this set
# @anti-pattern: A private range of controls (C0, DEL, U+2028) in one escaper
def hidden_in_source(char: str) -> bool:
    """True when *char* is a code point a reader of a source file cannot see.

    Not printable, a Default_Ignorable_Code_Point, or U+2800 BRAILLE PATTERN
    BLANK (the module docstring names each set). An escaper writes such a code
    point as an escape; a check over sources reports it.

    Args:
        char: One code point.

    Raises:
        ValueError: *char* is not exactly one code point.
    """
    code_point = _code_point(char)
    return (
        not char.isprintable()
        or code_point in _DEFAULT_IGNORABLE
        or code_point == BRAILLE_PATTERN_BLANK
    )


#: The hidden code points that shape text without reordering or hiding it: U+200C ZERO WIDTH
#: NON-JOINER and U+200D ZERO WIDTH JOINER, and the variation selectors.
TEXT_SHAPING_RANGES: Final[tuple[tuple[int, int], ...]] = (
    (0x200C, 0x200D),
    (0xFE00, 0xFE0F),
    (0xE0100, 0xE01EF),
)


def shapes_text(char: str) -> bool:
    """True when *char* is a code point that shapes text (:data:`TEXT_SHAPING_RANGES`)."""
    code_point = ord(char)
    return any(first <= code_point <= last for first, last in TEXT_SHAPING_RANGES)


#: The one flagged code point :func:`visible_text` keeps: the caller splits lines on it.
_LINE_FEED: Final[str] = "\n"
#: The last code point of the Basic Multilingual Plane, the last one spelled with four hex digits.
_LAST_BMP_CODE_POINT: Final[int] = 0xFFFF


# @canonical(text/visible-spelling): Write a hidden code point into a comment as visible text
# @rule: Every writer of author text into a comment, docstring or catalog comment calls this per physical line
# @anti-pattern: A string literal's escape (\uHHHH) inside a comment, which has no escape grammar
def visible_text(text: str) -> str:
    """*text* with each code point :func:`hidden_in_source` flags, other than LF, written as ``[U+HHHH]``.

    The hex is uppercase, four digits for a code point of the Basic Multilingual
    Plane and six for an astral one (``[U+200D]``, ``[U+0E0001]``). LF is kept:
    the caller splits lines on it. The output holds no flagged code point other
    than LF, so a second application changes nothing.

    Args:
        text: Author text bound for a comment.
    """
    return "".join(
        _spelled(char) if char != _LINE_FEED and hidden_in_source(char) else char
        for char in text
    )


def _spelled(char: str) -> str:
    code_point = ord(char)
    if code_point > _LAST_BMP_CODE_POINT:
        return f"[U+{code_point:06X}]"
    return f"[U+{code_point:04X}]"


def _code_point(char: str) -> int:
    if len(char) != 1:
        raise ValueError(
            f"Expected exactly one code point, got {len(char)} in {char!r}. Pass one character; "
            "to scan a string, call the predicate on each of its characters."
        )
    return ord(char)


_MAX_HEX_ESCAPE: Final[int] = 0xFF
_ASTRAL_BASE: Final[int] = 0x10000
_HIGH_SURROGATE_BASE: Final[int] = 0xD800
_LOW_SURROGATE_BASE: Final[int] = 0xDC00
_SURROGATE_PAYLOAD_BITS: Final[int] = 10
_SURROGATE_PAYLOAD_MASK: Final[int] = 0x3FF


class EscapeForm(Enum):
    """How a grammar spells a code point by its number inside a string literal."""

    UTF16_UNITS = "utf16-units"
    SIZED = "sized"
    BRACED = "braced"
    CHARACTER_REFERENCE = "character-reference"
    PLIST_UNITS = "plist-units"
    FOUR_OR_PLUS_SIX = "four-or-plus-six"
    FOUR_OR_EIGHT = "four-or-eight"


def _utf16_code_units(code_point: int) -> tuple[int, ...]:
    if code_point <= _LAST_BMP_CODE_POINT:
        return (code_point,)
    offset = code_point - _ASTRAL_BASE
    high = _HIGH_SURROGATE_BASE + (offset >> _SURROGATE_PAYLOAD_BITS)
    low = _LOW_SURROGATE_BASE + (offset & _SURROGATE_PAYLOAD_MASK)
    return (high, low)


def _utf16_units(code_point: int) -> str:
    return "".join(f"\\u{unit:04x}" for unit in _utf16_code_units(code_point))


def _plist_units(code_point: int) -> str:
    return "".join(f"\\U{unit:04x}" for unit in _utf16_code_units(code_point))


def _sized(code_point: int) -> str:
    if code_point <= _MAX_HEX_ESCAPE:
        return f"\\x{code_point:02x}"
    if code_point <= _LAST_BMP_CODE_POINT:
        return f"\\u{code_point:04x}"
    return f"\\U{code_point:08x}"


def _braced(code_point: int) -> str:
    return f"\\u{{{code_point:x}}}"


def _character_reference(code_point: int) -> str:
    return f"&#x{code_point:x};"


def _four_or_plus_six(code_point: int) -> str:
    if code_point <= _LAST_BMP_CODE_POINT:
        return f"\\{code_point:04x}"
    return f"\\+{code_point:06x}"


def _four_or_eight(code_point: int) -> str:
    if code_point <= _LAST_BMP_CODE_POINT:
        return f"\\u{code_point:04x}"
    return f"\\U{code_point:08x}"


_SPELLINGS: Final[dict[EscapeForm, Callable[[int], str]]] = {
    EscapeForm.UTF16_UNITS: _utf16_units,
    EscapeForm.SIZED: _sized,
    EscapeForm.BRACED: _braced,
    EscapeForm.CHARACTER_REFERENCE: _character_reference,
    EscapeForm.PLIST_UNITS: _plist_units,
    EscapeForm.FOUR_OR_PLUS_SIX: _four_or_plus_six,
    EscapeForm.FOUR_OR_EIGHT: _four_or_eight,
}


def _spelling(char: str, form: EscapeForm) -> str:
    return _SPELLINGS[form](ord(char))


# @canonical(text/hidden-code-point-escape): The spelling of a hidden code point inside a generated string literal
# @rule: A literal escaper handles its delimiters first, then passes the body through escape_hidden with its grammar's form
# @anti-pattern: A private control range (C0, DEL, U+2028) or a hand-written \\u spelling in one language's escaper
# @see: text/hidden-code-point
def escape_hidden(text: str, form: EscapeForm) -> str:
    """*text* with every code point :func:`hidden_in_source` flags spelled as an escape of *form*.

    Every other code point is left as it is, so text with no hidden code point is
    returned unchanged. The caller's escaper must already have escaped its escape
    character (the backslash, or ``&`` for ``CHARACTER_REFERENCE``): an escape
    written here then starts after an even run of backslashes, or after no bare
    ``&``, and reads as written.

    Args:
        text: A literal body whose delimiters and backslashes are already escaped.
        form: The spelling the literal's grammar decodes.

    Returns:
        The body with no hidden code point raw.
    """
    return "".join(
        _spelling(char, form) if hidden_in_source(char) else char for char in text
    )
