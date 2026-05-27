// PageTitleContext — lets a route page publish its current page title to
// the global TopNav center zone without TopNav re-fetching the data itself.
//
// Why not React Router `handle` metadata? The codebase uses the JSX router
// (`<Routes><Route .../></Routes>`), not the data-router `createBrowserRouter`
// API — `useMatches()` returns no handle for the JSX form. So we use a
// tiny context: each page calls `usePageTitle(name)` once data is loaded;
// TopNav reads it via `usePageTitleValue()`.
//
// Loading/error fallback: pages can pass `undefined` (or omit the call)
// and TopNav will render a fallback (e.g., the URL slug for /adong/:slug).
//
// Lifetime: the title resets when the page unmounts. No persistence across
// route changes — each page is responsible for its own title publication.

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';

interface PageTitleContextValue {
  title: string | undefined;
  setTitle: (next: string | undefined) => void;
}

const PageTitleContext = createContext<PageTitleContextValue | undefined>(
  undefined,
);

export function PageTitleProvider({ children }: { children: ReactNode }) {
  const [title, setTitle] = useState<string | undefined>(undefined);
  const value = useMemo(() => ({ title, setTitle }), [title]);
  return (
    <PageTitleContext.Provider value={value}>
      {children}
    </PageTitleContext.Provider>
  );
}

/** Read-only access — used by TopNav. */
export function usePageTitleValue(): string | undefined {
  const ctx = useContext(PageTitleContext);
  return ctx?.title;
}

/** Page hook: publish a title and clear it on unmount. Pass undefined to
 *  explicitly clear (e.g., during loading). */
export function usePageTitle(next: string | undefined): void {
  const ctx = useContext(PageTitleContext);
  useEffect(() => {
    if (!ctx) return;
    ctx.setTitle(next);
    return () => ctx.setTitle(undefined);
  }, [ctx, next]);
}
