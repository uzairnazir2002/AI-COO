@echo off
set SECRET_KEY=rAhqC7zsSGj0up1dMRaVklUP4tEio9TXc58IQFgYLbBxfH3OeyZKnm2wNDW6Jv
set DATABASE_URL=postgresql+asyncpg://ai_coo:ai_coo@localhost:5432/ai_coo
set REDIS_URL=redis://localhost:6379/0
set CORS_ORIGINS=http://localhost:3002,http://127.0.0.1:3002,http://localhost:3000,http://127.0.0.1:3000
cd /d c:\Project\AI COO\ai-coo\backend
"c:\Project\AI COO\ai-coo\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8001
