"""SQL dialect facts shared by every generator that emits relational DDL or migrations.

The type map, column derivation, identifier naming, dialect constants, the dialect
protocol with its concrete dialects and name-keyed registry, and the errors those
raise. The SQL generator's DDL path and each language generator's migration adapter
read them from here, so no language generator depends on the SQL generator.
"""
