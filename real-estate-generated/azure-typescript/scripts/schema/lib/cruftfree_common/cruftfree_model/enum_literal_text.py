"""The stored label of an enum member, from its name and declared value text alone.

On the standard library and ``identifier_case`` only, so code that reads a schema
after generation spells a stored enum label without loading the AST model.
"""

from __future__ import annotations

from cruftfree_common.utils.identifier_case import to_snake_case

__all__ = ["stored_enum_literal_from_parts"]


def stored_enum_literal_from_parts(member_name: str, declared_value: str | None) -> str:
    """The stored label from a member's name and declared value text.

    The form a schema snapshot carries a member in (``SnapshotEnum.values`` plus
    the parallel ``member_values``); produces exactly what
    :func:`~cruftfree_common.cruftfree_model.enum_literals.enum_member_stored_literal`
    produces for the same member.

    Args:
        member_name: The DSL member name (``PendingReview``).
        declared_value: Its ``value(...)`` as text, or ``None`` when it declares none.

    Returns:
        The stored label.
    """
    if declared_value is not None:
        return declared_value
    return to_snake_case(member_name)
