# DefiSys Control Center (Frontend)

![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)
![React](https://img.shields.io/badge/React-19-blue.svg)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-Dark_&_Tech-38B2AC.svg)

The **DefiSys Control Center** is the institutional-grade dashboard for the DefiSys V3 automated trading engine. It acts as an exclusive display and observation layer ("Smart Backend, Dumb Frontend") conforming to Audit Level 3.3 standards.

## 🌟 Modules (Phase 10)

1. **War Room (`/dashboard`)**:
   - Real-time monitoring of BTC/ETH prices and RPC Health (Latencies).
   - Market Activity indicators (RSI, Fear & Greed) dynamically synced.
   - Institutional Risk Protocol visualization.

2. **Sandbox Lab (`/dashboard/sandbox`)**:
   - Isolated environment to configure and run backtesting simulations without affecting production.
   - Interactive data visualization (Equity Curve, ROI, Max Drawdown) powered by Recharts.

3. **System Pulse (`/dashboard/pulse`)**:
   - Real-time log terminal powered by `xterm.js`.
   - Streams backend logs via WebSockets for deep observation of Trading Engine decisions and Multi-RPC failover alerts.
   - Preserves audit trails with history fetch.

## 🚀 Getting Started

### Local Development

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to view the Control Center.

### Production Build

```bash
npm run build
npm run start
```

## 🏗️ Architecture & Stack
- **Framework:** Next.js (App Router)
- **Styling:** Tailwind CSS (Dark & Tech UI)
- **Icons:** Lucide React
- **Data Visualization:** Recharts
- **Terminal:** xterm.js + xterm-addon-fit
- **Communication:** Native Fetch API & WebSockets (`useWebSocket` hook)
