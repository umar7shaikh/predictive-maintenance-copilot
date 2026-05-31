# Migrations

The app calls `Base.metadata.create_all` on startup for dev convenience, so the
schema exists without running Alembic. For production-style schema versioning:

```
# from backend/ with .env configured and Postgres reachable
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
