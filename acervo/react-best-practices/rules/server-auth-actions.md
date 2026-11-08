---
title: Authenticate Server Actions Like API Routes
impact: CRITICAL
impactDescription: prevents unauthorized access to server mutations
tags: server, server-actions, authentication, security, authorization
---

## Authenticate Server Actions Like API Routes

**Impact: CRITICAL (prevents unauthorized access to server mutations)**

Server Functions (functions marked with the `"use server"` directive, called "Server Actions" in some frameworks) are exposed as public endpoints, just like API routes, in any framework that supports React Server Components (Next.js, TanStack Start, Waku, and others). Always verify authentication and authorization **inside** each Server Function—do not rely solely on middleware, layout guards, or page-level checks, since they can be invoked directly with an arbitrary payload, bypassing whatever UI normally calls them.

Treat every Server Function with the same security considerations as a public-facing API endpoint: never assume the request came from your own UI.

This rule applies only to frameworks with a server (RSC-based meta-frameworks, or a hand-rolled API route/Route Handler backing a mutation). It has no equivalent in client-only routers (e.g., TanStack Router without TanStack Start) or in React Native/Expo apps that call a separate backend directly — there, apply the same principle to whatever backend endpoint performs the mutation.

**Incorrect (no authentication check):**

```typescript
'use server'

export async function deleteUser(userId: string) {
  // Anyone can call this! No auth check
  await db.user.delete({ where: { id: userId } })
  return { success: true }
}
```

**Correct (authentication inside the action):**

```typescript
'use server'

import { verifySession } from '@/lib/auth'
import { unauthorized } from '@/lib/errors'

export async function deleteUser(userId: string) {
  // Always check auth inside the action
  const session = await verifySession()
  
  if (!session) {
    throw unauthorized('Must be logged in')
  }
  
  // Check authorization too
  if (session.user.role !== 'admin' && session.user.id !== userId) {
    throw unauthorized('Cannot delete other users')
  }
  
  await db.user.delete({ where: { id: userId } })
  return { success: true }
}
```

**With input validation:**

```typescript
'use server'

import { verifySession } from '@/lib/auth'
import { z } from 'zod'

const updateProfileSchema = z.object({
  userId: z.string().uuid(),
  name: z.string().min(1).max(100),
  email: z.string().email()
})

export async function updateProfile(data: unknown) {
  // Validate input first
  const validated = updateProfileSchema.parse(data)
  
  // Then authenticate
  const session = await verifySession()
  if (!session) {
    throw new Error('Unauthorized')
  }
  
  // Then authorize
  if (session.user.id !== validated.userId) {
    throw new Error('Can only update own profile')
  }
  
  // Finally perform the mutation
  await db.user.update({
    where: { id: validated.userId },
    data: {
      name: validated.name,
      email: validated.email
    }
  })
  
  return { success: true }
}
```

Reference: [React docs - Server Functions](https://react.dev/reference/rsc/server-functions)
