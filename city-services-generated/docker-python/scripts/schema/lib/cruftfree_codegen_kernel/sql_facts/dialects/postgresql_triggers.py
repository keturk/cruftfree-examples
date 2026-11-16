"""PostgreSQL's realization of the table rules: PL/pgSQL functions and the triggers that call them.

An append-only table is guarded by one function and two triggers: a row trigger before every
update and delete, which lets an update through only when the row is the same apart from the
mutable columns, and a statement trigger before every truncate. The row is compared as a
document (``to_jsonb(NEW)`` against ``to_jsonb(OLD)``, the mutable keys removed from both),
so a column added to the table later is guarded without the function being rewritten.

An aggregate invariant is guarded by one function and one constraint trigger that is
deferrable and initially deferred, so it fires when the transaction commits, once for each
row the transaction touched: it re-aggregates the touched row's group (the rows sharing its
group columns' values) and refuses the commit unless the group's condition holds. A group
with no row left is never a violation.

The function bodies hold neither ``%`` nor ``:`` outside quoted text, so the statements pass
through a driver's text-statement escaping unchanged.
"""

from __future__ import annotations

from typing import Final

from cruftfree_common.utils.identifier_case import (
    DB_MAX_IDENTIFIER_LENGTH,
    truncate_identifier,
)
from cruftfree_common.utils.sql_text import dollar_quoted

from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    TriggerCreation,
    TriggerRemoval,
    TriggerStatement,
)

#: PostgreSQL's SQLSTATE for an attempt to change what a rule keeps unchanged (23001).
_APPEND_ONLY_ERRCODE: Final[str] = "restrict_violation"

#: PostgreSQL's SQLSTATE for a group of rows that violates its condition (23514).
_INVARIANT_ERRCODE: Final[str] = "check_violation"

#: Appended to an append-only rule's name for the trigger that guards truncates.
_TRUNCATE_SUFFIX: Final[str] = "truncate"


def truncate_trigger_name(name: str) -> str:
    """The name of the statement trigger that guards truncates of an append-only table.

    Capped at the identifier limit; the rule's name is shortened to make room for the suffix.
    """
    return truncate_identifier(
        name, DB_MAX_IDENTIFIER_LENGTH, separator="_", trailing=_TRUNCATE_SUFFIX
    )


class PostgreSQLTableTriggers:
    """The four table-rule statements of the ``SQLDialect`` protocol, in PostgreSQL."""

    def _function_statement(self, name: str, body: str) -> str:
        """``CREATE FUNCTION name() RETURNS trigger ...`` over the PL/pgSQL *body*."""
        return (
            f"CREATE FUNCTION {self.quote_identifier(name)}() RETURNS trigger "  # type: ignore[attr-defined]
            f"LANGUAGE plpgsql AS {dollar_quoted(body)};"
        )

    def _drop_trigger_statement(
        self, trigger: str, table_name: str
    ) -> TriggerStatement:
        return TriggerStatement(
            trigger,
            f"DROP TRIGGER {self.quote_identifier(trigger)} "  # type: ignore[attr-defined]
            f"ON {self.quote_identifier(table_name)};",  # type: ignore[attr-defined]
        )

    def render_drop_trigger_function(self, name: str) -> str:
        """See :meth:`TableTriggerStatements.render_drop_trigger_function`."""
        return f"DROP FUNCTION {self.quote_identifier(name)}();"  # type: ignore[attr-defined]

    def render_create_append_only_trigger(
        self, name: str, table_name: str, mutable_columns: tuple[str, ...]
    ) -> TriggerCreation:
        """See :meth:`TableTriggerStatements.render_create_append_only_trigger`."""
        quote_literal = self.quote_literal  # type: ignore[attr-defined]
        quote_identifier = self.quote_identifier  # type: ignore[attr-defined]
        keys = (
            f"CAST(ARRAY[{', '.join(quote_literal(column) for column in mutable_columns)}] AS text[])"
            if mutable_columns
            else "CAST(ARRAY[] AS text[])"
        )
        message = (
            "'table ' || TG_TABLE_NAME || ' is append-only: ' || TG_OP || ' is refused'"
        )
        body = (
            "BEGIN "
            "IF TG_OP = 'UPDATE' THEN "
            f"IF (to_jsonb(NEW) - {keys}) = (to_jsonb(OLD) - {keys}) THEN RETURN NEW; END IF; "
            "END IF; "
            f"RAISE EXCEPTION USING MESSAGE = {message}, ERRCODE = '{_APPEND_ONLY_ERRCODE}'; "
            "END"
        )
        table = quote_identifier(table_name)
        function = quote_identifier(name)
        truncate = truncate_trigger_name(name)
        return TriggerCreation(
            function=self._function_statement(name, body),
            triggers=(
                TriggerStatement(
                    name,
                    f"CREATE TRIGGER {function} BEFORE UPDATE OR DELETE ON {table} "
                    f"FOR EACH ROW EXECUTE FUNCTION {function}();",
                ),
                TriggerStatement(
                    truncate,
                    f"CREATE TRIGGER {quote_identifier(truncate)} BEFORE TRUNCATE ON {table} "
                    f"FOR EACH STATEMENT EXECUTE FUNCTION {function}();",
                ),
            ),
        )

    def render_drop_append_only_trigger(
        self, name: str, table_name: str
    ) -> TriggerRemoval:
        """See :meth:`TableTriggerStatements.render_drop_append_only_trigger`."""
        return TriggerRemoval(
            triggers=(
                self._drop_trigger_statement(truncate_trigger_name(name), table_name),
                self._drop_trigger_statement(name, table_name),
            ),
            function=self.render_drop_trigger_function(name),
        )

    def render_create_aggregate_invariant_trigger(
        self,
        name: str,
        table_name: str,
        group_columns: tuple[str, ...],
        predicate_sql: str,
    ) -> TriggerCreation:
        """See :meth:`TableTriggerStatements.render_create_aggregate_invariant_trigger`."""
        quote_identifier = self.quote_identifier  # type: ignore[attr-defined]
        table = quote_identifier(table_name)
        grouped = ", ".join(quote_identifier(column) for column in group_columns)
        message = (
            "'table ' || TG_TABLE_NAME || ' violates the invariant ' || TG_NAME || "
            "' at commit'"
        )

        def violation(row: str) -> str:
            same_group = " AND ".join(
                f"{quote_identifier(column)} = {row}.{quote_identifier(column)}"
                for column in group_columns
            )
            return (
                f"IF EXISTS (SELECT 1 FROM {table} WHERE {same_group} GROUP BY {grouped} "
                f"HAVING ({predicate_sql}) IS NOT TRUE) THEN "
                f"RAISE EXCEPTION USING MESSAGE = {message}, ERRCODE = '{_INVARIANT_ERRCODE}'; "
                "END IF; "
            )

        body = (
            "BEGIN "
            f"IF TG_OP IN ('INSERT', 'UPDATE') THEN {violation('NEW')}END IF; "
            f"IF TG_OP IN ('DELETE', 'UPDATE') THEN {violation('OLD')}END IF; "
            "RETURN NULL; "
            "END"
        )
        function = quote_identifier(name)
        return TriggerCreation(
            function=self._function_statement(name, body),
            triggers=(
                TriggerStatement(
                    name,
                    f"CREATE CONSTRAINT TRIGGER {function} AFTER INSERT OR UPDATE OR DELETE "
                    f"ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
                    f"EXECUTE FUNCTION {function}();",
                ),
            ),
        )

    def render_drop_aggregate_invariant_trigger(
        self, name: str, table_name: str
    ) -> TriggerRemoval:
        """See :meth:`TableTriggerStatements.render_drop_aggregate_invariant_trigger`."""
        return TriggerRemoval(
            triggers=(self._drop_trigger_statement(name, table_name),),
            function=self.render_drop_trigger_function(name),
        )
