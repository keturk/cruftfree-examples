"""Datasource configuration models.

Typed Pydantic models for RDBMS, cache, pubsub, nosql, and queue sections, one defining
module per family: ``models`` (the profile and per-kind config models), ``rdbms_engine``,
``cache_engine``, ``broker_engine``, ``nosql_engine``, ``queue_engine`` and
``identity_config``. Import each name from the module that defines it.

Unified service YAML embeds these under each profile; use
:class:`~cruftfree_common.config._unified_loader_unified_service_config.UnifiedServiceConfig` and
:func:`~cruftfree_common.config.unified_loader.load_service_config` to load and validate.
"""
