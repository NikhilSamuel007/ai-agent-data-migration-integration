# React frontend

React + TypeScript components render backend state and send consultant decisions through the typed REST client. Vite builds the application; Tailwind and custom CSS retain the existing workspace design.

```sh
cd frontend
npm install
npm run dev
```

Or use the included tested pnpm lockfile: `pnpm install --frozen-lockfile` then `pnpm run dev`.

Development UI: http://localhost:3000. Start `python backend/server.py` separately from the project root. To serve a production build, run `npm run build`, return to the root, then run `python frontend/server.py`.

- `src/App.tsx`: application state, actions, polling and navigation.
- `src/api.ts`: typed backend client; all mutations and reads use the API.
- `src/pages/`: dashboard, review queue, record results, audit trail.
- `src/components/`: editable escalation cards, stats, activity log, integration actions.
- `src/types.ts`: backend response contracts used by the UI.
- `public/config.js`: default browser API URL for Vite development.
- `server.py`: hosts `dist/` and supplies runtime `/config.js` from `API_BASE_URL`.

Production static host: `API_BASE_URL` defaults to http://localhost:8000. For Vite development edit `public/config.js` to change that URL. It must be reachable from the browser. Configure the same frontend origin in backend `FRONTEND_ORIGINS`. No private model or target credentials are included in browser configuration.

React state preserves in-progress edits while status polling continues. The UI never performs migration cleanup or decides that a write succeeded; outcomes come from the backend. Mapping cards show original samples, semantic rankings, Ollama reasoning when available, the policy score, and the detailed gate evidence.

The Dockerfile builds with Node in a separate stage, then serves the compiled result in a small Python runtime. Docker is not available in the authoring environment, so the image build remains unverified. Before production use, replace the prototype static host and add authenticated API access and TLS.
