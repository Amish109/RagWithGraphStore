# RagWithGraphStore


<!-- docker compose up -d && \
cd backend && \
uv run python -m uvicorn app.main:app --reload --port 8000
 & \
uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q celery -n upload@%h & \
uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q summaries -n summaries@%h & \
uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q entities -n entities@%h & \
wait -->

# docker compose up
<!-- docker compose up -d -->

# uv run python -m uvicorn app.main:app --reload --port 8000


# uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q celery -n upload@%h

# uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q summaries -n summaries@%h


# uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q entities -n entities@%h



# Delete Neo4j
- uv run python -m scripts.clear_neo4j


# Create admin user
- uv run python scripts/create_admin.py admin@gmail.com 123456

<!-- - uv run python scripts/create_admin.py admin@example.com admin -->
