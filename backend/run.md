# Start Docker Services
docker-compose up -d

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

---

# Create Admin User
uv run python scripts/create_admin.py admin@example.com admin

---

# API Docs
http://localhost:8000/docs

---

# Streamlit Frontend (If Using Python Frontend)

Install dependencies:
cd frontend && pip install -r requirements.txt

Start frontend:
cd frontend && streamlit run app.py

---

# Credentials

- Regular user → Register from frontend
- Admin user → Use create_admin.py script and login
