# Dashboard

This is the only active frontend in the repo.

## Local Development

```bash
npm ci
npm run dev
```

## Production Build

```bash
npm run build
```

## Vercel

Import the repository into Vercel from the repo root. The root `vercel.json` and `package.json` delegate the build into `dashboard/`.

Required environment variables:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

The older `ui/` Vite app has been retired.
