# Start Docker Services
docker-compose up -d

---

# Start Full Backend Stack With One Command
./scripts/start-backend.sh

---

# Backend API
cd backend && uv run uvicorn app.main:app --reload --port 8000

---

# Celery Workers (Named)

# Upload Worker
cd backend && uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q celery -n upload@%h

# Summary Worker
cd backend && uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q summaries -n summaries@%h

# Entities Worker
cd backend && uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q entities -n entities@%h

---

# Frontend (Next.js)
cd frontend-next && npm run dev

# Recommended if Turbopack keeps reloading/crashing
cd frontend-next && npx next dev --webpack

---

# Create Admin User
uv run python scripts/create_admin.py admin@example.com admin

---

# API Docs
http://localhost:8000/docs

---

# Credentials

- Regular user → Register from frontend
- Admin user → Use create_admin.py script and login
