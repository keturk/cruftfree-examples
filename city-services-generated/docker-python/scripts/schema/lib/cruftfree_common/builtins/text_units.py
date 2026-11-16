"""The ``String`` group's one unit and one whitespace set, for every target.

Every length, index and count a ``String`` builtin reads or returns -- ``length``,
``indexOf``, ``lastIndexOf``, ``substring``, ``slice``, ``charAt``, ``reverse``,
``padStart``/``padEnd`` and the ``Validator`` length checks -- counts Unicode code
points, so an emoji is one character on every target. ``trim``, ``trimStart``,
``trimEnd`` and ``isBlank`` remove or test for Unicode ``White_Space`` (the
property's 25 code points) and nothing else, so a byte order mark is never
whitespace and U+0085 always is.

``substring`` clamps each bound to ``[0, length]`` and swaps a reversed pair,
and ``slice`` counts a negative bound from the end (ECMAScript's rules; neither
throws). ``charAt`` refuses an index outside ``[0, length)`` rather than
answering a silent ``""``. ``capitalize`` upper-cases the first code point and
lower-cases the rest, and ``title`` does so to every space-separated word.

Written to be inlined: it imports nothing and has no module-scope side effects,
so a Python target copies this source into the code it generates; every other
target ports the same steps over code points.
"""

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
