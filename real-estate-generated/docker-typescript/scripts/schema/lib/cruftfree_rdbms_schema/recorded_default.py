"""The snapshot default a reflector records for a builtin call.

:func:`builtin_call_default` gives a reflector the default the extraction records
for a zero-argument builtin call, so a live snapshot states it as the source-built
one does. It imports only the snapshot model and the lowering's builtin table, so a
generated script that reflects a schema carries it.
"""

from __future__ import annotations

from cruftfree_rdbms_schema._snapshot_models import SnapshotDefault
from cruftfree_rdbms_schema.sql_lowering.builtins_table import LOWERING_BUILTINS, LoweringKey
from cruftfree_rdbms_schema.sql_lowering.lowered import BuiltinCall

#: The ``SnapshotDefault.kind`` of a function the database evaluates.
_SERVER_FUNCTION_DEFAULT_KIND = "server_function"


# @canonical(rdbms-schema/builtin-call-default): The snapshot default of a zero-argument
# builtin call, from its lowering row's key
# @rule: A default read back as a builtin's SQL records the call the extraction records for the same source
def builtin_call_default(key: LoweringKey) -> SnapshotDefault:
    """The default the extraction records for a zero-argument call of the builtin *key*.

    The call spelled as ``render_expression_source`` spells it (``uuid()``,
    ``DateTime.now()``), recorded as a ``server_function`` with its ``BuiltinCall``
    tree. A reflector that reads a column default back to its builtin
    (``builtin_call_for_sql``) records it through here, so the live snapshot states
    the default as the source-built one does.

    Raises:
        LookupError: *key* has no ``LOWERING_BUILTINS`` row, or its row takes
            operands, so no column default could have been written from it as a
            zero-argument call.
    """
    row = LOWERING_BUILTINS.get(key)
    if row is None or row.operands:
        raise LookupError(
            f"No lowering row of a builtin taking no operand for {key!r}, so no column "
            "default was written from it as a zero-argument call. Rows without operands: "
            f"{sorted(str(k) for k, r in LOWERING_BUILTINS.items() if not r.operands)}."
        )
    callee = key if isinstance(key, str) else ".".join(key)
    return SnapshotDefault(
        kind=_SERVER_FUNCTION_DEFAULT_KIND,
        value=f"{callee}()",
        name="server_default",
        tree=BuiltinCall(key),
    )
