---
title: Defer Non-Critical Third-Party Libraries
impact: MEDIUM
impactDescription: loads after hydration
tags: bundle, third-party, analytics, defer
---

## Defer Non-Critical Third-Party Libraries

Analytics, logging, and error tracking don't block user interaction. Load them after the app has mounted (and, on the web, after hydration) instead of bundling them into the initial chunk.

**Incorrect (blocks initial bundle):**

```tsx
import { Analytics } from 'some-analytics-sdk'

export default function App({ children }) {
  return (
    <>
      {children}
      <Analytics />
    </>
  )
}
```

**Correct (loads after mount):**

```tsx
import { lazy, Suspense } from 'react'

const Analytics = lazy(() =>
  import('some-analytics-sdk').then(m => ({ default: m.Analytics }))
)

export default function App({ children }) {
  return (
    <>
      {children}
      <Suspense fallback={null}>
        <Analytics />
      </Suspense>
    </>
  )
}
```

On the web, `React.lazy` still emits SSR markup for the fallback unless the framework supports skipping it (e.g. Next.js's `next/dynamic` with `{ ssr: false }`); when you need to guarantee the module never runs during SSR, use that framework-specific escape hatch instead.
