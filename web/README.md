# One Step — web

Next.js 16 (App Router) + TypeScript + Tailwind v4 + shadcn/ui. Mobile-first PWA.

```bash
cp .env.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                    # http://localhost:3000
npm run lint && npm run typecheck && npm run build
```

The page is a single client component (`src/components/kitchen.tsx`) that calls the API
(`src/lib/api.ts`) and remembers your last kitchen in `localStorage` (convenience only).
