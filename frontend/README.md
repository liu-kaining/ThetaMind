# ThetaMind Frontend

React + TypeScript frontend for the ThetaMind US Stock Option Strategy Analysis Platform.

## Tech Stack

- **Framework**: React 18 + Vite
- **Language**: TypeScript
- **UI**: Shadcn/UI + Tailwind CSS
- **State Management**: 
  - React Query (TanStack Query) for server state
  - Zustand for global app state
- **Routing**: React Router DOM
- **Charts**: 
  - Lightweight Charts (for candlesticks)
  - Recharts (for P&L area charts)
- **Authentication**: Google OAuth2 (@react-oauth/google)
- **Date/Time**: date-fns + date-fns-tz (for US/Eastern timezone)

## Setup

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Page components
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # Utility libraries (e.g., utils.ts)
│   ├── services/       # API service functions
│   ├── types/          # TypeScript type definitions
│   ├── utils/          # Helper functions
│   ├── App.tsx         # Main app component
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles (Tailwind)
├── public/             # Static assets
├── package.json
├── vite.config.ts      # Vite configuration
├── tsconfig.json       # TypeScript configuration
├── tailwind.config.js  # Tailwind CSS configuration
└── postcss.config.js   # PostCSS configuration
```

## Configuration

### Path Aliases

The project uses `@/*` alias pointing to `./src/*`:

```typescript
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
```

### API Proxy

Vite is configured to proxy `/api` requests to `http://localhost:8000`:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

### Timezone

All date/time operations should use `date-fns-tz` with `US/Eastern` timezone for market data display.

## Development Guidelines

- **TypeScript**: Strict mode enabled, no `any` types
- **Components**: Use Shadcn/UI components as base
- **State**: Use React Query for server state, Zustand for client state
- **Styling**: Tailwind CSS utility classes
- **Charts**: Lightweight Charts for candlesticks, Recharts for P&L

## Next Steps

1. Set up authentication flow (Google OAuth2)
2. Create API service layer
3. Implement core pages (Home, Strategy Builder, Analysis)
4. Integrate charts (Lightweight Charts + Recharts)
5. Add error boundaries and loading states

