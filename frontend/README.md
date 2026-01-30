# KundliHub Frontend

Vue 3 + Vite frontend for KundliHub.

See the root project README for full setup and deployment instructions:
- ../README.md

## Local dev

### API base URL

This app reads the backend base URL from a Vite environment variable:

- `VITE_API_BASE_URL` (example: `http://localhost:8000`)

Copy `.env.example` to `.env` and adjust if needed.

```bash
npm install
npm run dev
```
