---
title: Schedule Non-Blocking Work After the Response
impact: MEDIUM
impactDescription: faster response times
tags: server, async, logging, analytics, side-effects
---

## Schedule Non-Blocking Work After the Response

Send the response first, then run logging, analytics, and other side effects that the caller doesn't need to wait for. Blocking the response on work whose result nobody is waiting for adds latency for no benefit.

The API for this is runtime-specific — there's no single standard way to say "run this after I've responded, but don't let the process exit first":

- Next.js: `after()` from `next/server`
- Cloudflare Workers: `ctx.waitUntil()`
- Vercel Functions (outside Next.js): `waitUntil()` from `@vercel/functions`
- Plain Node.js server: nothing stops the response from flushing before an un-awaited promise settles, but the process must stay alive until it does — don't rely on `after`-style ordering guarantees on a server you don't control

Check what your framework or runtime exposes before assuming a generic fire-and-forget `void doWork()` is safe: on serverless/edge runtimes, the function can be frozen or torn down right after the response is sent, killing any promise that hasn't been explicitly registered to keep running.

**Incorrect (blocks response):**

```tsx
import { logUserAction } from '@/app/utils'

export async function POST(request: Request) {
  // Perform mutation
  await updateDatabase(request)
  
  // Logging blocks the response
  const userAgent = request.headers.get('user-agent') || 'unknown'
  await logUserAction({ userAgent })
  
  return new Response(JSON.stringify({ status: 'success' }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  })
}
```

**Correct (non-blocking, using Next.js's `after()` as an example):**

```tsx
import { after } from 'next/server'
import { logUserAction } from '@/app/utils'

export async function POST(request: Request) {
  // Perform mutation
  await updateDatabase(request)

  // Log after response is sent - the runtime keeps the function alive for this
  after(async () => {
    const userAgent = request.headers.get('user-agent') || 'unknown'
    logUserAction({ userAgent })
  })

  return new Response(JSON.stringify({ status: 'success' }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  })
}
```

The response is sent immediately while logging happens in the background. Swap `after()` for your runtime's equivalent (`ctx.waitUntil()`, `waitUntil()`, etc.) — the shape of the fix is the same, only the API differs.

**Common use cases:**

- Analytics tracking
- Audit logging
- Sending notifications
- Cache invalidation
- Cleanup tasks

**Important notes:**

- These APIs generally still run the callback even if the response fails or redirects
- Don't use plain `void asyncWork()` on serverless/edge runtimes as a substitute — without an explicit "keep running" registration, the runtime may tear down the function before the promise settles
