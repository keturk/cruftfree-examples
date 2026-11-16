"""The lowering of DSL expressions to SQL.

``builtins_table`` holds each DSL builtin's SQL per DDL dialect; ``lowered``
the tree of a lowered expression; ``dialect_rows`` each DDL dialect's quoting
and spelling; ``render`` the one renderer writing a tree for a dialect;
``tree_data`` a tree as plain data and back, for the snapshot to record;
``determinism`` whether a tree gives one value per row;
``lower`` the one lowering of an analyzed expression into a tree.

Every module of this subpackage but ``lower`` imports only the standard
library, this subpackage, and the quoting modules ``cruftfree_common.utils.sql_text``
and ``cruftfree_common.utils.hidden_text`` (themselves standard-library only): a
generated script carries these modules verbatim, so they reach nothing that a
generated project does not ship. ``lower`` runs at analysis and generation and
reads the analyzed model through ``cruftfree_common``; no carried module imports
it, so no script reaches it. Import each module by name; this package exports
nothing.
"""
