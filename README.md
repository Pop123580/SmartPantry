# SmartPantry

"Know what you have. Use what matters. Buy only what you need."

## Overview
SmartPantry tracks household groceries, predicts waste risk, recommends recipes using expiring ingredients, and helps you plan shopping intelligently. The intelligence and data persistence are powered exclusively by the backend API.

## Setup

```bash
npm install
npm run dev
```

## Architecture
- **React + Vite** for fast builds and HMR.
- **TypeScript** for type safety.
- **Tailwind v4** for responsive, mobile-first styling.
- **API Adapters**: All external data dependencies are abstracted into `src/services/adapters/fastapi`.

## Connecting the Backend
Read `docs/FRONTEND_BACKEND_HANDOFF.md` for instructions on connecting the FastAPI + Supabase backend.
The frontend expects a backend running at `VITE_API_BASE_URL` (default: `http://localhost:8000`).
