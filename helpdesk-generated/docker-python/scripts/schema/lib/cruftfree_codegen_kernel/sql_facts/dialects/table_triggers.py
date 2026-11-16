"""The statements that realize a database-enforced rule over a table's rows.

Two rules exist. An *append-only* table refuses every delete, every truncate and every
update that changes a column outside a listed few. An *aggregate invariant* requires every
group of rows (the rows sharing the values of some columns) to satisfy a condition over an
aggregate when a transaction commits. An engine realizes a rule as a function and the
triggers that call it (:class:`TriggerCreation`), and removes it as the triggers' drops and
the function's drop (:class:`TriggerRemoval`).

:class:`TableTriggerStatements` is the part of the ``SQLDialect`` protocol that spells them;
:class:`TableTriggerRefusals` is what ``DialectBase`` gives a dialect that does not override
them: each method refuses, naming the dialect and the rule.
"""

from __future__ import annotations

from typing import NoReturn, Protocol

from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    TriggerCreation,
    TriggerRemoval,
)
from cruftfree_codegen_kernel.sql_facts.errors import DialectFeatureError


class TableTriggerStatements(Protocol):
    """The statements of the table rules, as the ``SQLDialect`` protocol states them."""

    def render_create_append_only_trigger(
        self, name: str, table_name: str, mutable_columns: tuple[str, ...]
    ) -> TriggerCreation:
        """Render the rule that a table's rows are never deleted and updated only in *mutable_columns*.

        Every delete, every truncate and every update that changes a column outside
        *mutable_columns* is refused by the database, whoever issues it.

        Args:
            name: The rule's name, which names its function and its trigger.
            table_name: The table the rule governs.
            mutable_columns: The physical columns an update may change, sorted; empty
                when no update is allowed.

        Raises:
            DialectFeatureError: The engine has no trigger realization of the rule.
        """
        ...

    def render_drop_append_only_trigger(
        self, name: str, table_name: str
    ) -> TriggerRemoval:
        """Render the removal of the rule :meth:`render_create_append_only_trigger` creates."""
        ...

    def render_drop_trigger_function(self, name: str) -> str:
        """Render the statement that drops the function *name* a table rule's triggers call.

        A table dropped with its triggers leaves their function behind; this removes it.
        """
        ...

    def render_create_aggregate_invariant_trigger(
        self,
        name: str,
        table_name: str,
        group_columns: tuple[str, ...],
        predicate_sql: str,
    ) -> TriggerCreation:
        """Render the rule that every group of a table's rows satisfies *predicate_sql* at commit.

        A group is the rows sharing the values of *group_columns*; the rule re-checks the
        groups a statement touched when the transaction commits, so a transaction may pass
        through states that violate it. A violating commit is refused.

        Args:
            name: The rule's name, which names its function and its trigger.
            table_name: The table the rule governs.
            group_columns: The physical columns rows are grouped by, in declaration order.
            predicate_sql: The condition one group must satisfy, as the one SQL lowering
                renders it for this dialect, aggregate calls in place.

        Raises:
            DialectFeatureError: The engine has no trigger realization of the rule.
        """
        ...

    def render_drop_aggregate_invariant_trigger(
        self, name: str, table_name: str
    ) -> TriggerRemoval:
        """Render the removal of the rule :meth:`render_create_aggregate_invariant_trigger` creates."""
        ...


class TableTriggerRefusals:
    """What ``DialectBase`` gives a dialect that realizes no table rule: every method refuses."""

    def _refuse_trigger_rule(self, rule: str, name: str) -> NoReturn:
        """Raise: this dialect has no trigger realization of the table rule *rule*.

        Raises:
            DialectFeatureError: Always.
        """
        raise DialectFeatureError(
            f"The {self.name} dialect cannot realize the {rule} rule '{name}': the engine "  # type: ignore[attr-defined]
            "has no trigger realization of it. Only PostgreSQL has. Fix: declare the "
            "entity in an rdbms block of an engine that does."
        )

    def render_create_append_only_trigger(
        self, name: str, table_name: str, mutable_columns: tuple[str, ...]
    ) -> TriggerCreation:
        """Refuses: a dialect that does not override it does not realize the rule."""
        self._refuse_trigger_rule("append-only", name)

    def render_drop_append_only_trigger(
        self, name: str, table_name: str
    ) -> TriggerRemoval:
        """Refuses: a dialect that does not override it does not realize the rule."""
        self._refuse_trigger_rule("append-only", name)

    def render_drop_trigger_function(self, name: str) -> str:
        """Refuses: a dialect that does not override it does not realize the rules."""
        self._refuse_trigger_rule("table", name)

    def render_create_aggregate_invariant_trigger(
        self,
        name: str,
        table_name: str,
        group_columns: tuple[str, ...],
        predicate_sql: str,
    ) -> TriggerCreation:
        """Refuses: a dialect that does not override it does not realize the rule."""
        self._refuse_trigger_rule("aggregate invariant", name)

    def render_drop_aggregate_invariant_trigger(
        self, name: str, table_name: str
    ) -> TriggerRemoval:
        """Refuses: a dialect that does not override it does not realize the rule."""
        self._refuse_trigger_rule("aggregate invariant", name)
