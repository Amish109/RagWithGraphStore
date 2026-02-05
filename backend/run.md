⏺ Got it. Here's your setup:                                                                                                             
                                                                                                                                         
  Docker (3 services)                    
                                                                                                                                         
  docker run -d --name qdrant -p 6333:6333 qdrant/qdrant                                                                                 
  docker run -d --name redis -p 6379:6379 redis:7                                                                                        
  docker run -d --name postgres -p 5432:5432 -e POSTGRES_DB=ragapp -e POSTGRES_PASSWORD=password postgres:15
                                         
  backend/.env

  # Neo4j Aura (cloud)
  NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=your-aura-password

  # Local services (Docker)
  QDRANT_HOST=localhost
  QDRANT_PORT=6333
  REDIS_URL=redis://localhost:6379/0
  POSTGRES_URI=postgresql://postgres:password@localhost:5432/ragapp

  # Required
  SECRET_KEY=change-this-to-something-secure
  OPENAI_API_KEY=sk-your-openai-key

  Run

  cd backend
  pip install -r requirements.txt
  uvicorn app.main:app --reload --port 8000

  API docs at http://localhost:8000/docs



  Install frontend dependencies:
  cd frontend && pip install -r requirements.txt
  3. Start the frontend:
  cd frontend && streamlit run app.py
  4. Test Login Flow (AUTH-F01):
    - Navigate to http://localhost:8501
    - See Login and Register pages in navigation
    - Enter email and password
    - Click Login
    - Should see Home page with sidebar showing user info
  5. Test Debug Panel (AUTH-F06):
    - Click Debug in navigation
    - Verify User ID is displayed
    - Verify Token Expires countdown is shown
  6. Test Logout Flow (AUTH-F03):
    - Click Logout button in sidebar
    - Should return to Login page
  7. Test Registration Flow (AUTH-F02):
    - Click Register in navigation
    - Enter new email, password, confirm password
    - Click Register
    - Should immediately see Home page
  8. Test Anonymous Session (AUTH-F04):
    - Without logging in, observe sidebar
    - Should show "Anonymous Session"
  9. Test Sidebar User Info (AUTH-F05):
    - When logged in, sidebar shows email, role, session type



  python scripts/create_admin.py admin@example.com yourpassword                                                                                                                     



                                                                                                                                                                                    
  Summary of credentials:                                  
  - Regular user: Register through the frontend (any email/password)
  - Admin user: Run the script above, then login with those credentials
