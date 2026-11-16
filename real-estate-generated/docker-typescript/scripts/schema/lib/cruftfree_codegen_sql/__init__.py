"""SQL DDL generator for CruftFree.

Produces raw SQL scripts from RdbmsBlock entities.
Supports every registered DDL dialect (PostgreSQL today).

The SQL dialect facts this generator builds on -- the type map, column
derivation, naming, dialects and their errors -- live in
``cruftfree_codegen_kernel.sql_facts`` and are imported from there.
"""
