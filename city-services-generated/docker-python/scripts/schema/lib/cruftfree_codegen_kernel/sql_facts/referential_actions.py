"""The SQL keyword each DSL referential action renders as.

Every emitter of a relational foreign key -- the SQL generator's DDL and each
language generator's ORM declaration and migration adapter -- spells
``ON DELETE``/``ON UPDATE`` through this one table, so a constraint the DDL
creates and the constraint a migration re-creates never disagree.
"""

from __future__ import annotations

from collections.abc import Mapping

from cruftfree_common.cruftfree_model.constants import VALID_REFERENTIAL_ACTIONS
from cruftfree_common.errors.generation import GenerationError
from cruftfree_common.utils.identifier_case import to_snake_case

#: The SQL spelling of each DSL referential action
#: (:data:`~cruftfree_common.cruftfree_model.constants.VALID_REFERENTIAL_ACTIONS`).
#: ANSI keywords, identical on every dialect: the camelCase action's words,
#: upper-cased (``setNull`` -> ``SET NULL``).
SQL_REFERENTIAL_ACTIONS: Mapping[str, str] = {
    action: to_snake_case(action).replace("_", " ").upper()
    for action in sorted(VALID_REFERENTIAL_ACTIONS)
}


# @canonical(sql/referential-action-keyword): DSL referential action -> SQL ON DELETE/ON UPDATE keyword
# @rule: Every relational FK emitter (DDL, ORM declaration, migration) spells actions through this
# @anti-pattern: Emitting a DSL action verbatim (``ON DELETE setNull``) or reading the ORM cascade(...) modifier as a SQL action
# @see: sql/referential-action-from-keyword
def sql_referential_action(action: str) -> str:
    """The SQL keyword for one DSL referential action.

    Args:
        action: A DSL action (``cascade``, ``restrict``, ``setNull``).

    Returns:
        The ``ON DELETE``/``ON UPDATE`` keyword.

    Raises:
        GenerationError: *action* is not a DSL referential action -- emitting
            it verbatim would write DDL the database rejects (``ON DELETE
            setNull``).
    """
    keyword = SQL_REFERENTIAL_ACTIONS.get(action)
    if keyword is None:
        raise GenerationError(
            f"Unknown referential action '{action}' in a foreign key. Expected one of: "
            f"{sorted(SQL_REFERENTIAL_ACTIONS)}. The schema snapshot records DSL actions; "
            f"regenerate the snapshot if it holds a SQL keyword."
        )
    return keyword


#: The referential actions an ENGINE can report on a live foreign key: the DSL's three and
#: the two SQL defines beyond them (``NO ACTION`` is what a constraint created with no
#: clause means; ``SET DEFAULT`` is engine-only). A reflected key may hold either of the
#: two, and a snapshot must be able to say so -- it then differs from any DSL action.
ENGINE_REFERENTIAL_KEYWORDS: frozenset[str] = frozenset(
    {*SQL_REFERENTIAL_ACTIONS.values(), "NO ACTION", "SET DEFAULT"}
)


# @canonical(sql/referential-action-from-keyword): SQL ON DELETE/ON UPDATE keyword an engine reports -> the snapshot's action vocabulary
# @rule: Every reflector records a live foreign key's action through this, so a reflected snapshot and a source-built one compare action for action
# @anti-pattern: Recording the raw catalog keyword (``CASCADE``) in a snapshot whose source-built side holds ``cascade`` -- every key would then look changed
def dsl_referential_action(keyword: str) -> str:
    """The snapshot action an engine-reported referential keyword stands for.

    The inverse of :func:`sql_referential_action`: ``CASCADE`` -> ``cascade``,
    ``SET NULL`` -> ``setNull``. The two keywords outside the DSL (``NO ACTION``,
    ``SET DEFAULT``) map to ``noAction`` / ``setDefault``: not DSL actions, so a live key
    holding one compares unequal to every action the source can declare, which is
    exactly what the differ must see to replace the key.

    Args:
        keyword: A referential keyword as an engine reports it (any case).

    Returns:
        The snapshot action.

    Raises:
        GenerationError: *keyword* is not a referential action any engine defines.
    """
    normalized = " ".join(keyword.strip().upper().split())
    if normalized not in ENGINE_REFERENTIAL_KEYWORDS:
        raise GenerationError(
            f"Unknown referential action keyword '{keyword}' reported for a foreign key. "
            f"Expected one of: {sorted(ENGINE_REFERENTIAL_KEYWORDS)}."
        )
    first, *rest = normalized.lower().split()
    return first + "".join(word.capitalize() for word in rest)


__all__ = [
    "ENGINE_REFERENTIAL_KEYWORDS",
    "SQL_REFERENTIAL_ACTIONS",
    "dsl_referential_action",
    "sql_referential_action",
]
