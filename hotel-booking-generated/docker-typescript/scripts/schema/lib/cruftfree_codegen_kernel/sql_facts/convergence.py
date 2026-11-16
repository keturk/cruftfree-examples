"""A convergence plan: the SQL that brings a block's live catalog to its declared schema.

:func:`converge` plans one RDBMS block from ``L``, its catalog as the block's reader parsed it
from one consistent read, and ``D``, its schema as generation wrote it. The changes and their
outcomes are the migration package's (:func:`~cruftfree_rdbms_schema.convergence.convergence_changes`);
this module renders them through the block's SQL dialect and puts them behind the guards an
apply needs.

The previous release keeps serving while the new one starts, so a plan splits its applied
changes into two phases, each change in the phase its outcome has
(:func:`~cruftfree_rdbms_schema.change_policy.convergence_phase`): **expand**, applied before the new
release starts, and **contract**, applied once it is healthy. Each phase is one apply, its SQL in
the order it runs:

* the **lock guard** -- takes the block's session lock, keyed by its ``rdbms_id`` (the same
  lock a catalog read takes), or stops the apply when another session holds it;
* the **fingerprint guard** -- recomputes the digest of the catalog read the plan was computed
  from and stops the apply when the catalog moved since;
* the **apply's transaction** -- its begin, the schema prelude (whose search path lasts for
  the transaction), every change of the phase
  (:func:`~cruftfree_codegen_kernel.sql_facts.revision.render_convergence_by_change`), its
  commit; a failed change ends the client, and the server rolls back every change of the
  transaction before it. On a dialect whose added enum labels are usable only once committed
  (``FEATURE_ENUM_LABEL_COMMITTED_BEFORE_USE``), a phase that adds a label runs two: the
  label additions (with the renames of their types) commit first, then every other change,
  so a default, check or table naming a new label meets it committed;
* the **catalog statement** -- the read's own composed statement, which prints the catalog the
  apply left with its length and digest, for the client to check as it checks a read;
* the **release guard** -- releases the lock, and fails when the apply did not hold it.

No change runs before both guards. The guards print nothing, and every line of a phase's SQL
belongs to exactly one guard, the transaction's begin or commit, the schema prelude, the catalog
statement or one change (:meth:`PlanPhase.statement_at`), so a failed line of an apply names what
failed. A phase with no change to apply writes no SQL. A change that needs approval is refused
unless *approved* is true, and the plan carries the SQL it would run; a change no forward DDL
realizes is never in the SQL. The plan carries ``L`` as it compared it, so whether the block
holds ``D`` is answered from the same comparison.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from cruftfree_rdbms_schema._canonicalize_rules import LiveCatalogFacts
from cruftfree_rdbms_schema.change_policy import (
    ConvergenceOutcome,
    ConvergenceOutcomeKind,
    ConvergencePhase,
    convergence_phase,
)
from cruftfree_rdbms_schema.convergence import ConvergenceChanges, convergence_changes
from cruftfree_rdbms_schema.differ import ChangeKind

from cruftfree_codegen_kernel.sql_facts.constants import (
    FEATURE_ENUM_LABEL_COMMITTED_BEFORE_USE,
)
from cruftfree_codegen_kernel.sql_facts.dialects.catalog_read import catalog_fingerprint
from cruftfree_codegen_kernel.sql_facts.dialects.dialect_statements import session_lock_for
from cruftfree_codegen_kernel.sql_facts.revision import render_convergence_by_change
from cruftfree_codegen_kernel.sql_facts.type_mappings import live_type_resolver

if TYPE_CHECKING:
    from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot
    from cruftfree_rdbms_schema.catalog_reader import CatalogQuery
    from cruftfree_rdbms_schema.differ import SchemaChange

    from cruftfree_codegen_kernel.sql_facts._revision_model import ChangeStatement
    from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
        SessionLockSql,
    )
    from cruftfree_codegen_kernel.sql_facts.dialects.base import SQLDialect

__all__ = [
    "ApplyFrame",
    "ConvergencePlan",
    "PlanPhase",
    "PlanStatement",
    "RefusedChange",
    "apply_frame",
    "converge",
    "fingerprint_guard",
    "lock_guard",
    "release_guard",
]

logger = logging.getLogger(__name__)

#: Ends every line of a plan's SQL.
_LINE_BREAK: Final[str] = "\n"

#: The changes a leading enum-label transaction commits: the label additions, and the
#: renames of the types they add to, which they follow (:func:`_label_transaction_first`).
_LABEL_TRANSACTION_KINDS: Final[frozenset[ChangeKind]] = frozenset(
    {ChangeKind.ENUM_TYPE_RENAMED, ChangeKind.ENUM_VALUE_ADDED}
)


def lock_guard(block: str) -> str:
    """The error the lock guard raises when another session holds *block*'s lock."""
    return (
        f"The schema of block '{block}' is being read or changed by another session, which "
        "holds the block's lock. The apply did not start and no change ran; run the deploy "
        "again once that session has finished."
    )


def fingerprint_guard(block: str, fingerprint: str) -> str:
    """The error the fingerprint guard raises when *block*'s catalog moved after its read."""
    return (
        f"The catalog of block '{block}' changed after the read this plan was computed from "
        f"(fingerprint {fingerprint}). The apply stopped before any change ran; read the "
        "catalog again and plan from that read."
    )


def release_guard(block: str) -> str:
    """The error the release guard raises when the apply did not hold *block*'s lock."""
    return (
        f"The apply of block '{block}' did not hold the block's lock when it released it, so "
        "another session may have changed the schema while it ran. Read the catalog again "
        "and compare it with the declared schema."
    )


@dataclass(frozen=True)
class PlanStatement:
    """One statement of a convergence plan's SQL, and what owns it.

    Attributes:
        owner: What the statement is, as a failed apply names it: one of the guards, the
            transaction's begin or commit, the schema prelude, the catalog statement, or the
            change it renders.
        change: The change it renders; ``None`` for any other statement.
        sql: Its SQL text, as the dialect renders it.
    """

    owner: str
    change: SchemaChange | None
    sql: str


@dataclass(frozen=True)
class RefusedChange:
    """A change the plan refuses until the deploy runs with ``--approved``.

    Attributes:
        block: The block's ``rdbms_id``.
        outcome: The change and its needs-approval diagnostic, which names the change, why it
            needs approval and the fix (run the deploy again with ``--approved``, or change the
            DSL).
        sql: The statements that apply it, as an approved deploy runs them.
    """

    block: str
    outcome: ConvergenceOutcome
    sql: tuple[str, ...]

    @property
    def message(self) -> str:
        """The refusal as the schema tool prints it: the block, the diagnostic, then the SQL."""
        statements = _LINE_BREAK.join(self.sql)
        return (
            f"Block '{self.block}': {self.outcome.diagnostic} The SQL it runs once approved:"
            f"{_LINE_BREAK}{statements}"
        )


@dataclass(frozen=True)
class PlanPhase:
    """One phase of a convergence plan: the SQL of one apply, and what owns each statement.

    Attributes:
        phase: When the apply runs: before the new release starts, or once it is healthy.
        applied: The applied changes this phase runs, in render order; each is in exactly
            the phase its outcome has (``convergence_phase``).
        statements: The SQL's statements in the order they run, each owned by one guard, the
            transaction's begin or commit, the schema prelude, the catalog statement or one
            change; empty when the phase applies no change.
    """

    phase: ConvergencePhase
    applied: tuple[ConvergenceOutcome, ...]
    statements: tuple[PlanStatement, ...]

    @property
    def lines(self) -> tuple[tuple[str, PlanStatement], ...]:
        """Every line of the phase's SQL, in order, paired with the statement it belongs to."""
        return tuple(
            (line, statement)
            for statement in self.statements
            for line in statement.sql.split(_LINE_BREAK)
        )

    @property
    def sql(self) -> str:
        """The SQL as an apply's client reads it: every line, each ended by a line break."""
        return "".join(f"{line}{_LINE_BREAK}" for line, _ in self.lines)

    def statement_at(self, line: int) -> PlanStatement | None:
        """The statement line *line* (numbered from 1) of the SQL belongs to; ``None`` past it."""
        lines = self.lines
        if 1 <= line <= len(lines):
            return lines[line - 1][1]
        return None


@dataclass(frozen=True)
class ConvergencePlan:
    """What it takes to bring one block's live catalog to its declared schema.

    Attributes:
        block: The block's ``rdbms_id``.
        live: ``L`` as the plan compared it (``ConvergenceChanges.live``): prepared for
            comparison, so table names are ``D``'s, nothing it holds is set aside, and it
            is not canonicalized. Whether the block holds ``D`` is
            ``require_same_schema(live, D)``.
        fingerprint: The digest of the catalog read ``L`` was parsed from.
        approved: Whether the deploy ran with ``--approved``.
        applied: The changes the SQL applies, in render order; with *approved* the changes
            that need approval among them.
        refused: With *approved* false, the changes that need approval, each with its SQL.
        never_applied: The changes no forward DDL realizes, each diagnostic giving the reason
            and the fix; never in the SQL.
        lock: The block's session lock, which each phase's SQL takes first and releases last.
        expand: The applied changes that run before the new release starts, and their SQL.
        contract: The applied changes that run once the new release is healthy, and their
            SQL.
    """

    block: str
    live: RdbmsSchemaSnapshot
    fingerprint: str
    approved: bool
    applied: tuple[ConvergenceOutcome, ...]
    refused: tuple[RefusedChange, ...]
    never_applied: tuple[ConvergenceOutcome, ...]
    lock: SessionLockSql
    expand: PlanPhase
    contract: PlanPhase

    @property
    def risky(self) -> tuple[ConvergenceOutcome, ...]:
        """The applied changes that rows the generator cannot see may fail, naming the constraint."""
        return tuple(
            outcome
            for outcome in self.applied
            if outcome.kind is ConvergenceOutcomeKind.APPLIED_RISKY
        )

    @property
    def phases(self) -> tuple[PlanPhase, PlanPhase]:
        """Both phases, in the order a deploy applies them: expand, then contract."""
        return (self.expand, self.contract)


def _change_owner(block: str, change: SchemaChange) -> str:
    """How a failed apply names *change*: its kind and the object it is about."""
    subject = (
        ".".join(part for part in (change.entity, change.field) if part)
        or change.enum
        or change.detail
    )
    about = f" of '{subject}'" if subject else ""
    return f"the {change.kind.value} change{about} in block '{block}'"


def _owned(block: str, rendered: Sequence[ChangeStatement]) -> list[PlanStatement]:
    """*rendered* as plan statements, each owned by its change or by the schema prelude."""
    return [
        PlanStatement(
            owner=(
                f"the schema prelude of block '{block}'"
                if item.change is None
                else _change_owner(block, item.change)
            ),
            change=item.change,
            sql=item.statement.sql,
        )
        for item in rendered
    ]


def _refused(
    block: str, changes: ConvergenceChanges, dialect: SQLDialect
) -> tuple[RefusedChange, ...]:
    """Every refused change of *changes*, with the statements an approved deploy runs for it."""
    return tuple(
        RefusedChange(
            block=block,
            outcome=outcome,
            sql=tuple(
                item.statement.sql
                for item in render_convergence_by_change(
                    changes.live, changes.desired, (outcome.change,), dialect
                )
                if item.change is not None
            ),
        )
        for outcome in changes.refused
    )


@dataclass(frozen=True)
class ApplyFrame:
    """The statements every phase's apply shares: what it opens with, and what follows its commit.

    A plan writes it around each phase's transaction, and an apply re-renders it to refuse a
    file that is not one of the block's plan files.

    Attributes:
        opening: The lock guard, the catalog search path (``catalog_search_path_sql``, which
            the read sets too, so the guard and the catalog statement compute the document
            the read did), then the fingerprint guard of the read the plan came from.
        closing: The catalog statement, then the release guard.
    """

    opening: tuple[PlanStatement, PlanStatement, PlanStatement]
    closing: tuple[PlanStatement, PlanStatement]


def apply_frame(
    block: str,
    fingerprint: str,
    lock: SessionLockSql,
    dialect: SQLDialect,
    catalog_queries: Sequence[CatalogQuery],
) -> ApplyFrame:
    """The guards of *block*'s apply and the catalog statement between its commit and release.

    The catalog statement is the read's own composer (``catalog_document_sql``), so the
    catalog the apply left is printed with its length and digest exactly as a read prints it.

    Raises:
        ValueError: *fingerprint* is not a read's digest, or the queries do not compose.
        DialectFeatureError: The dialect cannot spell a guard or the catalog statement.
    """
    return ApplyFrame(
        opening=(
            PlanStatement(
                owner=f"the lock guard of block '{block}'",
                change=None,
                sql=dialect.abort_unless_sql(lock.try_acquire_condition, lock_guard(block)),
            ),
            PlanStatement(
                owner=f"the search path of block '{block}'",
                change=None,
                sql=dialect.catalog_search_path_sql(catalog_queries),
            ),
            PlanStatement(
                owner=f"the fingerprint guard of block '{block}'",
                change=None,
                sql=dialect.catalog_fingerprint_guard_sql(
                    catalog_queries, fingerprint, fingerprint_guard(block, fingerprint)
                ),
            ),
        ),
        closing=(
            PlanStatement(
                owner=f"the catalog statement of the apply of block '{block}'",
                change=None,
                sql=dialect.catalog_document_sql(catalog_queries),
            ),
            PlanStatement(
                owner=f"the release guard of block '{block}'",
                change=None,
                sql=dialect.abort_unless_sql(lock.release_condition, release_guard(block)),
            ),
        ),
    )


def _label_transaction_first(
    applied: tuple[ConvergenceOutcome, ...], dialect: SQLDialect
) -> tuple[tuple[ConvergenceOutcome, ...], tuple[ConvergenceOutcome, ...]]:
    """*applied* as the outcomes a leading enum-label transaction commits, and the rest.

    On a dialect whose added enum labels are usable only once committed
    (``FEATURE_ENUM_LABEL_COMMITTED_BEFORE_USE``), a phase that adds a label commits its
    label additions, with the renames of the types they add to, before every other change:
    a default, a check, a backfill or a table creation naming a new label runs after that
    commit. The leading part is empty when the dialect needs no such commit or the phase
    adds no label, and the phase runs in one transaction.
    """
    if not dialect.supports_feature(FEATURE_ENUM_LABEL_COMMITTED_BEFORE_USE) or not any(
        outcome.change.kind is ChangeKind.ENUM_VALUE_ADDED for outcome in applied
    ):
        return (), applied
    leading = tuple(o for o in applied if o.change.kind in _LABEL_TRANSACTION_KINDS)
    rest = tuple(o for o in applied if o.change.kind not in _LABEL_TRANSACTION_KINDS)
    return leading, rest


def _transaction(
    block: str,
    owner: str,
    outcomes: tuple[ConvergenceOutcome, ...],
    changes: ConvergenceChanges,
    dialect: SQLDialect,
) -> list[PlanStatement]:
    """*outcomes*' changes behind the schema prelude, between *owner*'s begin and commit."""
    rendered = render_convergence_by_change(
        changes.live, changes.desired, tuple(outcome.change for outcome in outcomes), dialect
    )
    return [
        PlanStatement(owner=f"the begin of {owner}", change=None, sql=dialect.apply_begin_sql()),
        *_owned(block, rendered),
        PlanStatement(owner=f"the commit of {owner}", change=None, sql=dialect.apply_commit_sql()),
    ]


def _plan_phase(
    block: str,
    phase: ConvergencePhase,
    changes: ConvergenceChanges,
    dialect: SQLDialect,
    frame: ApplyFrame,
) -> PlanPhase:
    """*phase*'s changes of *changes* behind *frame*'s guards, in one transaction or two.

    A transaction holds its changes behind the schema prelude, whose search path lasts for
    the transaction only, so they commit together or none does. The phase's changes run in
    one transaction, unless it adds an enum label the dialect makes usable only once
    committed: then the label additions commit first, in a transaction of their own
    (:func:`_label_transaction_first`), and every other change runs in a second one. A
    phase that applies no change holds no statement: there is nothing to guard.
    """
    applied = tuple(
        outcome for outcome in changes.applied if convergence_phase(outcome.kind) is phase
    )
    if not applied:
        return PlanPhase(phase=phase, applied=(), statements=())
    apply = f"the {phase.value} apply of block '{block}'"
    leading, rest = _label_transaction_first(applied, dialect)
    body: list[PlanStatement] = []
    if leading:
        body.extend(
            _transaction(block, f"the enum label transaction of {apply}", leading, changes, dialect)
        )
    if rest:
        body.extend(_transaction(block, apply, rest, changes, dialect))
    statements = (*frame.opening, *body, *frame.closing)
    return PlanPhase(phase=phase, applied=applied, statements=statements)


def _plan_phases(
    block: str,
    changes: ConvergenceChanges,
    fingerprint: str,
    lock: SessionLockSql,
    dialect: SQLDialect,
    catalog_queries: Sequence[CatalogQuery],
) -> tuple[PlanPhase, PlanPhase]:
    """The expand and the contract phase of *changes*; both empty when nothing is applied."""
    if not changes.applied:
        return (
            PlanPhase(phase=ConvergencePhase.EXPAND, applied=(), statements=()),
            PlanPhase(phase=ConvergencePhase.CONTRACT, applied=(), statements=()),
        )
    frame = apply_frame(block, fingerprint, lock, dialect, catalog_queries)
    return (
        _plan_phase(block, ConvergencePhase.EXPAND, changes, dialect, frame),
        _plan_phase(block, ConvergencePhase.CONTRACT, changes, dialect, frame),
    )


# @canonical(sql/convergence-plan): The SQL that brings a block's live catalog L to its declared
#   schema D, in an expand and a contract phase, each behind the lock and fingerprint guards,
#   with the changes refused until approved and the changes never applied
# @rule: Every applied change is in exactly one phase, the one its outcome has (convergence_phase)
# @rule: No change of either phase runs before the lock guard and the fingerprint guard of the
#   read L came from
# @rule: A needs-approval change is in the SQL only with `approved`; a never-applied change never
# @rule: Every line of a phase's SQL belongs to exactly one guard, the transaction's begin or
#   commit, the schema prelude, the catalog statement or one change
# @rule: A phase's changes run in one transaction: they commit together or none does -- except
#   that on a dialect whose added enum labels are usable only once committed, a phase adding a
#   label commits its label additions first, in a transaction of their own
# @rule: A phase's SQL prints the catalog it left through the read's own composed statement,
#   after its commit and before its release guard
# @rule: A phase with no change to apply writes no SQL
# @rule: The plan carries L as it compared it, so whether a block holds D is
#   require_same_schema(plan.live, D), never a second planner path
# @see: rdbms-schema/convergence-changes
# @see: sql/session-lock
def converge(
    live: RdbmsSchemaSnapshot,
    desired: RdbmsSchemaSnapshot,
    approved: bool,
    fingerprint: str,
    *,
    dialect: SQLDialect,
    catalog_queries: Sequence[CatalogQuery],
) -> ConvergencePlan:
    """Plan what it takes to bring *live* to *desired* on *dialect*.

    Args:
        live: ``L``, the block's catalog as its reader parsed it (no table and no enum for
            an empty database).
        desired: ``D``, the block's schema as generation wrote it.
        approved: True exactly when the deploy was run with ``--approved``.
        fingerprint: The verified digest of the catalog read *live* was parsed from.
        dialect: The block's SQL dialect; its name is the DDL dialect the live engine speaks.
        catalog_queries: The read's catalog queries, bound to the block's places, which the
            fingerprint guard and the catalog statement read again.

    Returns:
        The plan: ``L`` as it compared it, its changes by outcome and the SQL of each phase.

    Raises:
        ValueError: *fingerprint* is not a read's digest (64 lowercase hex digits), the
            queries do not compose (``catalog_read_queries``), or a change is malformed.
        GenerationError: The dialect declares no session lock, *live* lacks an object a
            change removes, or a change cannot be rendered.
        DialectFeatureError: The dialect cannot spell a guard, the catalog statement or a
            change's statement.
    """
    verified = catalog_fingerprint(fingerprint)
    block = desired.rdbms_id
    facts = LiveCatalogFacts(stored_type=live_type_resolver(dialect.name), ddl_dialect=dialect.name)
    changes = convergence_changes(live, desired, approved, facts)
    lock = session_lock_for(dialect, block)
    expand, contract = _plan_phases(block, changes, verified, lock, dialect, catalog_queries)
    plan = ConvergencePlan(
        block=block,
        live=changes.live,
        fingerprint=verified,
        approved=approved,
        applied=changes.applied,
        refused=_refused(block, changes, dialect),
        never_applied=changes.never_applied,
        lock=lock,
        expand=expand,
        contract=contract,
    )
    logger.debug(
        "converge block=%s dialect=%s applied=%d refused=%d never_applied=%d "
        "expand_statements=%d contract_statements=%d",
        block,
        dialect.name,
        len(plan.applied),
        len(plan.refused),
        len(plan.never_applied),
        len(expand.statements),
        len(contract.statements),
    )
    return plan
