# Frontend Conventions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Vue 3 Composition API + `<script setup>` |
| Language | TypeScript (strict mode) |
| Build | Vite |
| Router | vue-router (role-based dynamic imports) |
| State | Pinia |
| HTTP Client | axios (via `src/services/api/`) |
| Testing | vitest + jsdom |
| Lint | ESLint + Prettier |
| Type Check | vue-tsc --noEmit |

---

## Three-Layer Architecture

Frontend code is strictly divided into three layers with non-negotiable boundaries:

```
┌──────────────────────────────────────┐
│            Pages                      │  ← permission isolation + layout, minimal CSS
├──────────────────────────────────────┤
│        Business Components            │  ← API layer + base composition, fixed CSS specs
├──────────────────────────────────────┤
│        Base Components                │  ← pure UI + interaction + animation, no business
└──────────────────────────────────────┘
```

### Dependency Rules

- **Base Components** → no dependencies on other layers
- **Business Components** → may depend on base components + composables
- **Pages** → may depend on business components + base components

Cross-layer dependencies are forbidden: pages must not use composables directly (pages don't deal with API), base components must not depend on business components.

---

## Layer 1: Base Components

**Directory:** `src/components/ui/` or `core/`

### Three Iron Rules (Non-negotiable)

| # | Rule | Explanation |
|---|------|-------------|
| 1 | **No API calls** | No `fetch`, `axios`, `api.get`, `api.post` inside the component |
| 2 | **Universal** | Not coupled to any business scenario; fully parameterized via props |
| 3 | **No business logic** | No business field names, business conditionals, or business routing |

### Styling Rules

- Self-contained styles with `scoped`
- Expose customizable theme points via **CSS variables** (colors, spacing, border-radius)
- Animations and transitions are implemented at this layer

```vue
<!-- ✅ Correct -->
<script setup lang="ts">
defineProps<{
  type?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
}>()
const emit = defineEmits<{ click: [e: MouseEvent] }>()
</script>
<style scoped>
.ar-button {
  padding: var(--btn-padding, 8px 16px);
  border-radius: var(--btn-radius, 6px);
  transition: all 0.2s ease;
}
</style>
```

```vue
<!-- ❌ Wrong: API call in base component -->
<script setup lang="ts">
import { api } from '@/services/api'
async function handleClick() {
  const { data } = await api.get('/posts')  // forbidden!
}
</script>
```

```vue
<!-- ❌ Wrong: business field names in base component -->
<script setup lang="ts">
defineProps<{
  postTitle: string     // forbidden — business term in base component
  postStatus: string
}>()
</script>
```

### Existing Base Components (Ar series)

`ArButton`, `ArTag`, `ArAvatar`, `ArBadge`, `ArDivider`, `ArTable`, `ArPagination`, `ArCarousel3D`, `ArWheelPicker`, `ArScrollbar`, `ArPopconfirm`, `ArTopNav`, `ArSideNav`

---

## Layer 2: Business Components

**Directory:** `src/components/blog/`, `src/components/admin/`, `src/components/user/`, etc.

### Core Principles

- Compose multiple base components for business functionality
- **API calls happen here, but must go through composables**
- All CSS specs are **fixed explicitly** — every scene, boundary, and size is defined in CSS
- State management (Pinia) **starts at this layer at minimum**

### API Call Rule

> ❌ **Forbidden:** Calling `api.xxx()` directly in `.vue` files
> ✅ **Required:** Encapsulate API calls in composables

```vue
<!-- ✅ Correct -->
<script setup lang="ts">
import { usePostList } from '@/composables/usePostList'
const { posts, loading, fetch } = usePostList()
</script>
```

```vue
<!-- ❌ Wrong -->
<script setup lang="ts">
import { api } from '@/services/api'
const { data } = await api.get('/posts')  // forbidden
</script>
```

### CSS Rules

- All specs are fixed — no external CSS variable overrides
- Every scene (list mode, grid mode, empty, loading, error) has an explicit CSS class
- Use `scoped` styles

```css
/* ✅ Correct */
.post-card--list { gap: 16px; padding: 12px 16px; border-radius: 8px; }
.post-card--grid { aspect-ratio: 3/4; border-radius: 12px; }
```

---

## Layer 3: Pages

**Directory:** `src/views/`

### Core Principles

- Only two responsibilities: **permission isolation** + **layout composition**
- CSS volume is **near zero** — at most layout properties (`display`, `flex`, `grid`, `gap`)
- ❌ No color, font-size, padding, margin, or background in page styles
- ❌ No direct API calls

```vue
<!-- ✅ Correct -->
<template>
  <ArPageContainer>
    <PostFilterBar />
    <PostGrid>
      <PostCard v-for="post in posts" :key="post.id" :post="post" />
    </PostGrid>
    <ArPagination :page="page" :total="total" @change="handlePageChange" />
  </ArPageContainer>
</template>
<style scoped>
/* layout-only CSS */
.post-list-page { display: flex; flex-direction: column; gap: 24px; }
</style>
```

```vue
<!-- ❌ Wrong -->
<style scoped>
.post-list-page {
  color: #333;          /* forbidden */
  font-size: 14px;      /* forbidden */
  padding: 16px;        /* forbidden */
  background: #fff;     /* forbidden */
}
</style>
```

---

## CSS Responsibility Summary

| Layer | CSS Volume | Responsibility | Boundary |
|-------|-----------|---------------|----------|
| Base | Heavy | Visual + animation + CSS variable API | scoped, no external deps |
| Business | Medium | Fixed specs for all scenes | scoped, no overrides accepted |
| Pages | ≤5 lines | Layout only (flex/grid/gap) | ❌ No color/font/spacing |

**CR Red Line:** Any page with more than 5 lines of CSS or non-layout style properties is rejected outright.

---

## API Call Convention

### Directory Structure

```
src/composables/
├── usePostList.ts
├── usePostDetail.ts
├── useTagSuggestions.ts
└── ...
```

### Standard Pattern

```typescript
// composables/usePostList.ts
import { ref } from 'vue'
import { api } from '@/services/api'
import type { BlogPost } from '@/services/api'

export function usePostList() {
  const posts = ref<BlogPost[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch(params?: { page?: number; page_size?: number }) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/posts', { params })
      posts.value = data
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  return { posts, loading, error, fetch }
}
```

---

## Code Splitting by Role

| Role | Router | Components | Chunk loaded |
|------|--------|-----------|--------------|
| Guest (unauthenticated) | GuestLayout | blog/ | Blog chunk only |
| Authenticated user | PlatformShell | blog/ + user/ | Blog + Platform chunks |
| Admin | ConsoleLayout | blog/ + user/ + admin/ | All chunks |

Vite dynamic imports:

```typescript
const AdminRoutes = () => import("@/views/admin/AdminDashboard.vue");
```

## Routing Convention

Role-based route files:

```
src/router/
├── index.ts           # Main router setup
├── blog-routes.ts     # Public routes
├── platform-routes.ts # Authenticated routes
└── admin-routes.ts    # Admin routes
```

## Component Naming

- Multi-word component names (Vue style guide recommendation)
- Prefix with area: `BlogPost`, `AdminUserTable`, `UserMenu`
- File names: `PascalCase.vue`

## Testing

```bash
npm run test:run       # Single run (vitest + jsdom)
npm run test           # Watch mode
```

Test files co-locate with components: `ComponentName.spec.ts`
