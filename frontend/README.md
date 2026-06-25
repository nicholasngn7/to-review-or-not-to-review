# MR Review Council — Frontend

React + TypeScript + Vite app for MR Review Council.

## Setup

```bash
npm install
npm run dev
```

The dev server runs at `http://localhost:5173`. Requests to `/api/*` are proxied
to the backend at `http://localhost:8000` (see `vite.config.ts`).

## Scripts

| Command           | Description                       |
| ----------------- | --------------------------------- |
| `npm run dev`     | Start the Vite dev server         |
| `npm run build`   | Type-check and build for production |
| `npm run preview` | Preview the production build      |

## Layout

```text
src/
  main.tsx     # React entrypoint
  App.tsx      # Landing page
  App.css      # Page styles
  index.css    # Global styles / theme tokens
```
