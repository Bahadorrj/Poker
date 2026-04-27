## 0.2.0 (2026-04-28)

### Feat

- **test**: implement base configurations for testing and introduce base tests in test_db.py and test_tables.py

### Fix

- **alembic**: ensure sqlalchemy.url is a synchronous database URL to allow migrations

### Refactor

- rename cash_in to buy_in; add alembic revision for renaming the cash_in column in the `players` table
