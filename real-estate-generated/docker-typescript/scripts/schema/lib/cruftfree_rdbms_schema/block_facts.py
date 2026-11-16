"""What the schema runtime needs to know of an RDBMS block beyond its schema.

A schema snapshot carries no engine, provider, platform or language, so the facts a
generated script reads (the engine's name, the DDL dialect it renders and reflects
in, and the oldest server it reads) are a second record, written beside the snapshot at
generation and read back after it. The record and its JSON codec import only the
standard library and the errors, so a generated script carries them.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, fields
from typing import Final, get_type_hints

from cruftfree_common.errors.generation import GenerationError


@dataclass(frozen=True, slots=True)
class BlockFacts:
    """The facts of one RDBMS block a generated script reads beside its snapshot.

    Attributes:
        engine: The engine's canonical name (``postgres``).
        ddl_dialect: The DDL dialect the engine's DDL and DML are rendered and
            reflected in (``postgresql``).
        minimum_server_version: The oldest server the block's schema is read from,
            as the engine numbers its versions (PostgreSQL's ``server_version_num``,
            ``130000``); an older server is refused before the read.
    """

    engine: str
    ddl_dialect: str
    minimum_server_version: int


def _non_empty_string(key: str, value: object) -> str:
    """*value* when it is a non-empty string, else refused naming *key*."""
    if not isinstance(value, str) or not value:
        raise GenerationError(
            f"The block facts document's '{key}' is {value!r}, not a non-empty string. "
            "Regenerate the facts."
        )
    return value


def _positive_integer(key: str, value: object) -> int:
    """*value* when it is a positive integer (a JSON ``true`` is not one), else refused naming *key*."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GenerationError(
            f"The block facts document's '{key}' is {value!r}, not a positive integer. "
            "Regenerate the facts."
        )
    return value


def _as_is(value: object) -> object:
    """*value* unchanged: a string or an integer is its own JSON value."""
    return value


@dataclass(frozen=True, slots=True)
class _ValueCodec:
    """How a facts value of one record field type is written and read back.

    Attributes:
        encode: The JSON value a field's value is written as.
        decode: The check a JSON value takes, returning the field's value or
            refusing it naming the key.
    """

    encode: Callable[[object], object]
    decode: Callable[[str, object], object]


#: The codec a facts value takes, by the type of its record field.
_VALUE_CODECS: Final[dict[object, _ValueCodec]] = {
    str: _ValueCodec(encode=_as_is, decode=_non_empty_string),
    int: _ValueCodec(encode=_as_is, decode=_positive_integer),
}


def _field_codecs() -> dict[str, _ValueCodec]:
    """Each record field's name and the codec its type takes, in field order.

    Raises:
        TypeError: A field's type has no codec in ``_VALUE_CODECS``.
    """
    hints = get_type_hints(BlockFacts)
    codecs: dict[str, _ValueCodec] = {}
    for field in fields(BlockFacts):
        field_type = hints[field.name]
        if field_type not in _VALUE_CODECS:
            raise TypeError(
                f"BlockFacts.{field.name} is typed {field_type!r}, which has no codec. "
                f"Expected one of {sorted(repr(kind) for kind in _VALUE_CODECS)}: add its codec "
                "to _VALUE_CODECS."
            )
        codecs[field.name] = _VALUE_CODECS[field_type]
    return codecs


#: The keys a facts document holds, the record's field names each exactly once, with the
#: codec of each key's value.
_KEY_CODECS: Final[dict[str, _ValueCodec]] = _field_codecs()

#: The keys a facts document holds, in field order.
_BLOCK_FACTS_KEYS: Final[tuple[str, ...]] = tuple(_KEY_CODECS)


def encode_block_facts(facts: BlockFacts) -> str:
    """The facts document for *facts*: a JSON object, sorted keys, 2-space indent."""
    document = {key: codec.encode(getattr(facts, key)) for key, codec in _KEY_CODECS.items()}
    return json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False)


def decode_block_facts(data: str) -> BlockFacts:
    """Read a facts document back into its record.

    Args:
        data: The JSON text :func:`encode_block_facts` wrote.

    Returns:
        The block's facts.

    Raises:
        GenerationError: The text is not JSON, is not a JSON object, lacks a key,
            holds a key the record does not have, or holds a value its field's
            type refuses (a string value that is not a non-empty string, an
            integer value that is not a positive integer); the message names the key.
    """
    try:
        parsed: object = json.loads(data)
    except json.JSONDecodeError as error:
        raise GenerationError(
            f"The block facts document is not valid JSON: {error}. "
            f"Expected a JSON object with the keys {list(_BLOCK_FACTS_KEYS)}."
        ) from error
    if not isinstance(parsed, dict):
        raise GenerationError(
            f"The block facts document is a JSON {type(parsed).__name__}, not an object. "
            f"Expected a JSON object with the keys {list(_BLOCK_FACTS_KEYS)}."
        )
    unknown = sorted(str(key) for key in parsed if key not in _BLOCK_FACTS_KEYS)
    if unknown:
        raise GenerationError(
            f"The block facts document holds the unknown key(s) {unknown}. "
            f"Expected exactly the keys {list(_BLOCK_FACTS_KEYS)}: regenerate the facts "
            "with the generator that reads them."
        )
    values: dict[str, object] = {}
    for key, codec in _KEY_CODECS.items():
        if key not in parsed:
            raise GenerationError(
                f"The block facts document has no '{key}' key. "
                f"Expected exactly the keys {list(_BLOCK_FACTS_KEYS)}: regenerate the facts."
            )
        values[key] = codec.decode(key, parsed[key])
    return BlockFacts(**values)


__all__ = ["BlockFacts", "decode_block_facts", "encode_block_facts"]
