# DefiSys Control Center v3.0

Institutional-grade frontend dashboard for the DefiSys V3 automated trading engine. Follows a "Smart Backend, Dumb Frontend" architecture (Audit Level 3.3).

## Tech Stack

- **Framework**: Next.js 16+ (App Router, Webpack mode)
- **React**: 19
- **Styling**: Tailwind CSS 4 with custom dark theme
- **Real-time**: WebSocket via custom `useWebSocket` hook
- **Charts**: Recharts (equity curves)
- **Terminal**: xterm.js + xterm-addon-fit (System Pulse)
- **Icons**: Lucide React
- **Language**: TypeScript

## Project Structure

```
src/
├── app/
│   ├── api/                    # BFF proxy routes to Go/Python backend
│   │   ├── sandbox/run/        # POST: trigger simulation
│   │   ├── system/health/      # GET: RPC node health
│   │   ├── system/indicators/  # GET: RSI, F&G, regime
│   │   └── system/logs/        # GET: audit log tail
│   ├── dashboard/
│   │   ├── layout.tsx          # Sidebar + TickerHeader layout
│   │   ├── page.tsx            # War Room (main)
│   │   ├── sandbox/page.tsx    # Strategy Backtesting Lab
│   │   └── pulse/page.tsx      # Real-time Audit Console
│   ├── login/page.tsx
│   ├── layout.tsx              # Root layout
│   └── globals.css             # Global styles, custom scrollbar, animations
├── components/
│   ├── Sidebar.tsx             # Collapsible left nav with module links
│   ├── TickerHeader.tsx        # Top bar: prices, RPC nodes status
│   └── IndicatorWidget.tsx     # RSI / Fear&Greed / Regime gauge cards
├── hooks/
│   └── useWebSocket.ts         # WS hook with exponential backoff reconnect
└── lib/
    ├── backendEndpoints.ts     # Environment-aware URL builders
    └── bffProxy.ts             # BFF proxy utility
```

## Dashboard Modules

| Module | Route | Description |
|---|---|---|
| War Room | `/dashboard` | Market intelligence, risk protocol, system console |
| Sandbox Lab | `/dashboard/sandbox` | Historical backtesting with XGBoost params |
| System Pulse | `/dashboard/pulse` | Real-time log streaming via WebSocket + xterm |

## Backend Connectivity

- Backend expected at `http://backend:8000` (configurable via `API_BASE_URL` env var)
- WebSocket base: `ws://backend:8000` (configurable via `WS_BASE_URL`)
- All API calls go through Next.js BFF route handlers (relative URLs)
- Graceful fallback UI when backend is offline

## Workflow

- **Command**: `PORT=5000 npx next dev --webpack`
- **Port**: 5000 (webview)

## Design System

- Dark theme: `slate-950` base, `slate-900` cards, `slate-800` borders
- Accent colors: cyan (War Room), violet (Sandbox), emerald (System Pulse)
- Custom scrollbar, grid background, glow utilities in globals.css
- Sidebar is collapsible (click arrow at bottom)
