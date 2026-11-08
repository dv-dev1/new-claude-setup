---
title: Dynamic Imports for Heavy Components
impact: CRITICAL
impactDescription: directly affects TTI and LCP
tags: bundle, dynamic-import, code-splitting, lazy, suspense
---

## Dynamic Imports for Heavy Components

Use `React.lazy()` with `Suspense` to lazy-load large components not needed on initial render, instead of bundling them into the initial chunk.

**Incorrect (Monaco bundles with main chunk ~300KB):**

```tsx
import { MonacoEditor } from './monaco-editor'

function CodePanel({ code }: { code: string }) {
  return <MonacoEditor value={code} />
}
```

**Correct (Monaco loads on demand):**

```tsx
import { lazy, Suspense } from 'react'

const MonacoEditor = lazy(() =>
  import('./monaco-editor').then(m => ({ default: m.MonacoEditor }))
)

function CodePanel({ code }: { code: string }) {
  return (
    <Suspense fallback={<Skeleton />}>
      <MonacoEditor value={code} />
    </Suspense>
  )
}
```

**Framework-specific loaders:** meta-frameworks and routers often wrap this pattern with extra features (route-level code splitting, SSR opt-out, preloading) — e.g. Next.js's `next/dynamic`, TanStack Router's lazy route modules, or Expo Router's lazy screens. Prefer the framework's loader when one exists; fall back to `React.lazy` + `Suspense` otherwise.
