// Shared ESC-to-close hook.
//
// Centralizes the `useEffect → window.addEventListener('keydown') →
// if (e.key === 'Escape') close()` pattern used by dismissible UI.
//
// Behavior:
//   - Listens on `window` for `keydown` while `enabled` is true.
//   - On Escape: calls `e.stopPropagation()` then `handler()`.
//   - When `enabled` flips to false, the listener is removed.
//   - When `handler` identity changes, listener rebinds (fresh closure).
//
// Each open component can register its own handler. Passing `enabled={isOpen}`
// keeps the side-effects scoped.
//
// Usage:
//   useEscapeKey(onClose, isOpen);

import { useEffect } from 'react';

export function useEscapeKey(
  handler: () => void,
  enabled: boolean = true,
): void {
  useEffect(() => {
    if (!enabled) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        handler();
      }
    };

    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [handler, enabled]);
}
