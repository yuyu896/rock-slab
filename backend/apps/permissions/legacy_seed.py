"""Compatibility hooks for the retired role-based permission migration.

Roles no longer imply operation grants or management scopes. These functions
remain importable for migration history and callers that referenced the old
helpers, but intentionally do not read or write authorization data.
"""


def seed_legacy_grants(apps=None):
    """Do not infer or create authorization records from a user's role."""


def reverse_legacy_grants(apps=None):
    """A migration rollback must never delete explicitly managed grants."""
