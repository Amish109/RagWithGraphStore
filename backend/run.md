docker-compose up -d 
uv run uvicorn app.main:app --reload


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
