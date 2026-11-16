"""Where the schema tool keeps each RDBMS block's documents, beside ``schema.py``, and how it prints.

The generator writes them (``dgen/schema_tool.py``) and the tool's commands read them, so
both take the names from here: ``desired/<block key>.json``, the block's schema snapshot, and
``facts/<block key>.json``, its engine facts. Every command prints its result through
:func:`print_output`, so what a deploy script reads is byte for byte what the command wrote.
"""

from __future__ import annotations

import sys
from typing import Final

#: The directory, beside ``schema.py``, holding each block's desired snapshot.
DESIRED_DIR_NAME: Final[str] = "desired"

#: The directory, beside ``schema.py``, holding each block's engine facts.
FACTS_DIR_NAME: Final[str] = "facts"

#: The suffix every block document's name ends with, after its block key.
BLOCK_DOCUMENT_SUFFIX: Final[str] = ".json"

#: The encoding of everything a command prints on standard output.
OUTPUT_ENCODING: Final[str] = "utf-8"


def block_document_name(block_key: str) -> str:
    """The file name of *block_key*'s desired snapshot and of its engine facts."""
    return f"{block_key}{BLOCK_DOCUMENT_SUFFIX}"


def print_output(text: str) -> None:
    """Write *text* on standard output as its UTF-8 bytes, nothing translated.

    A command's output is a client's input or a verified document, read byte for byte by the
    deploy script that ran the command. Standard output in text mode would end each line with
    the platform's line ending (``\\r\\n`` on Windows) and encode in the console's code page, so
    the bytes go to the underlying buffer instead.
    """
    sys.stdout.flush()
    sys.stdout.buffer.write(text.encode(OUTPUT_ENCODING))
    sys.stdout.buffer.flush()
