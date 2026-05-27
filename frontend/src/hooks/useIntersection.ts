// Intersection Observer hook.
//
// Used by R-3 AdongDetail to detect when the hero leaves the viewport so the
// scroll-sticky pill rail (page-local action group, D-3) can fade in from
// bottom-right. Single observer per consumer; reused if more "is X in
// viewport?" needs appear.
//
// Lifecycle notes:
//   - Returns `true` initially (safe default — assume in view until the first
//     callback). Prevents the pill rail from flashing on mount before the
//     observer reports.
//   - Observer is created in useEffect, disconnected on unmount AND on any
//     dependency change (so navigating /adong/A → /adong/B rebuilds the
//     observer for the new hero).
//   - Caller passes a stable ref. Inline option objects are fine because we
//     destructure threshold/root/rootMargin — only those primitives are
//     dependencies, so a fresh `{}` literal each render does NOT cause churn.
//
// Usage:
//   const heroRef = useRef<HTMLElement>(null);
//   const heroVisible = useIntersection(heroRef);
//   // ... <PillRail visible={!heroVisible} /> ...

import { useEffect, useState } from 'react';
import type { RefObject } from 'react';

export interface UseIntersectionOptions {
  /** 0 = any pixel intersects; 1 = fully inside. Default 0. */
  threshold?: number | number[];
  /** Custom scroll root. Default: viewport. */
  root?: Element | Document | null;
  /** Margin around the root. Default: '0px'. */
  rootMargin?: string;
}

export function useIntersection(
  ref: RefObject<Element | null>,
  options: UseIntersectionOptions = {},
): boolean {
  const { threshold = 0, root = null, rootMargin = '0px' } = options;
  // Safe default: assume intersecting until observer reports otherwise.
  const [intersecting, setIntersecting] = useState(true);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') return; // SSR safety

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry) setIntersecting(entry.isIntersecting);
      },
      { threshold, root, rootMargin },
    );

    observer.observe(el);
    return () => observer.disconnect();
    // Depend on the primitive option values, not the wrapping object — that
    // way an inline `{}` at the call site doesn't cause observer churn each
    // render. The ref itself is stable across renders by design.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ref, threshold, root, rootMargin]);

  return intersecting;
}
