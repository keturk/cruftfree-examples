"""Configuration models and utilities.

The package re-exports nothing: every name is imported from the module that
declares it (``cruftfree_common.config.env_ref.EnvRef``,
``cruftfree_common.config.deployment_plan.DeploymentPlan``, ...), so importing one
config module never loads the others and each symbol has one import path.
"""
