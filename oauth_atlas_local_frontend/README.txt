OAuth Atlas — local frontend starter

WHAT THIS IS
A single-file HTML/CSS/JavaScript frontend for your existing FastAPI OAuth guide backend.
No npm, React, Lovable credits, or extra frontend libraries are required.

BEFORE YOU START
1. Make sure your backend .env includes:
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173
2. Start your backend from the project root:
   python -m uvicorn app.main:app --reload --port 8000
3. Open a NEW PowerShell window.
4. Navigate to the folder containing index.html, for example:
   cd "D:\Documents\Product\assignments\Composio_OAuth\oauth_guide_frontend"
   (Put this folder inside your existing project folder, or adjust the path.)
5. Start the static frontend server:
   python -m http.server 3000 --bind 127.0.0.1
6. Open:
   http://localhost:3000

IMPORTANT
- Keep the backend terminal and frontend terminal running.
- Do not open index.html by double-clicking; use http://localhost:3000.
- The frontend calls http://127.0.0.1:8000/api/guides/generate.
- If the request fails, check backend logs and CORS_ORIGINS.
- This is for local testing. A publicly hosted frontend needs a publicly reachable backend URL.
- The UI currently displays the generated guide returned by POST. The persistent guide ID is displayed and can be copied. If you want a shareable page that reloads a saved guide by ID, we can add the exact GET endpoint once confirmed from /docs.
