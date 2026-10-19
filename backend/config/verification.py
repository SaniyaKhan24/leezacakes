class NoDatabaseRouter:
    """Skip migration-history connections during database-free verification."""

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return False
