# SmartPantry Frontend-Backend Handoff

## Project Architecture
The frontend is a React SPA built with Vite, TypeScript, and Tailwind v4.
It uses a strict layered architecture:
`UI Components -> Custom Hooks -> API Interface -> FastAPI Adapter (fetch calls)`

## Where API Calls Live
All API definitions and actual `fetch` implementations are in `src/services/adapters/fastapi/*Api.ts`.
The frontend expects a backend running at `VITE_API_BASE_URL`.

## How to Connect the Backend
1. Look at `src/services/adapters/fastapi/fastapiPantryApi.ts` (and others).
2. The current implementation uses standard `fetch()` to `http://localhost:8000/api/...`.
3. If your FastAPI routes differ slightly, simply update the URLs in those adapter files.
4. If your JSON response structure differs slightly from the TypeScript interfaces in `src/types/`, you can map the response directly inside the API adapter. For example: `return data.map(dbItem => ({ id: dbItem._id, name: dbItem.title, ... }))`.
5. The UI components will not need to be touched as long as the adapter layer transforms your backend response into the types defined in `src/types/`.

## No Fake Intelligence
The frontend explicitly **does not** mock intelligence. If the backend returns 0 items for OCR, the UI will show 0 items. If the backend returns 15 recipes, the UI will render all 15. The UI renders the real state returned by the FastAPI server. Loading, empty, and error states are implemented gracefully in all components.
