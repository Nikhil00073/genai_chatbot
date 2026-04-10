# FastAPI + React Chat Starter

This workspace provides a minimal chat app with:

- A FastAPI backend exposing `POST /chat`
- Direct calls to either the OpenAI API or the Anthropic Claude API
- A mock mode for testing without any API key
- A React frontend that sends a message and renders the response

## Project layout

```text
backend/
  app/
    chat_service.py
    main.py
  .env.example
  requirements.txt
frontend/
  .env.example
  src/
    App.jsx
    main.jsx
    styles.css
  index.html
  package.json
  vite.config.js
```

## Backend setup

1. Create a Python virtual environment in `backend/`
2. Install dependencies:

   ```powershell
   pip install -r backend/requirements.txt
   ```

3. Copy the example environment file and fill in your provider details:

   ```powershell
   Copy-Item backend/.env.example backend/.env
   ```

  For local testing without any external credentials, keep `AI_PROVIDER=mock`.

4. Start the API server:

   ```powershell
   uvicorn app.main:app --app-dir backend --reload
   ```

The backend runs on `http://localhost:8000` by default.

## Frontend setup

1. Install dependencies:

   ```powershell
   cd frontend
   npm install
   ```

2. If your backend is not on port 8000, copy the frontend env file and update the API URL:

  ```powershell
  Copy-Item frontend/.env.example frontend/.env
  ```

  Then set `VITE_API_URL` to the backend origin, for example `http://127.0.0.1:8001`.

3. Start the Vite dev server:

   ```powershell
   npm run dev
   ```

The frontend runs on `http://localhost:5173` by default and sends requests to `http://localhost:8000`.

## API contract

`POST /chat`

Request body:

```json
{
  "message": "Write a short welcome message for my app."
}
```

Response body:

```json
{
  "reply": "Welcome to the app...",
  "provider": "openai",
  "model": "gpt-4.1-mini"
}
```

## Testing without an API key

Use `AI_PROVIDER=mock` in `backend/.env`.

Mock mode keeps the same frontend and backend flow, but the backend generates a local response instead of calling OpenAI or Anthropic.

## Notes for this workspace

- Port 8000 is already occupied in the current environment.
- The backend was validated successfully on `http://127.0.0.1:8001/health`.
- To make the frontend call that backend instance, set `VITE_API_URL=http://127.0.0.1:8001` in `frontend/.env`.
