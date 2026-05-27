// Shared ESC-to-close hook.
//
// Replaces 4+ duplicated `keydown` listeners across Modal, AdongPanel,
// TransactionPanel, KernelScorePanel (and R-1 CriteriaPanel later). All five
// previously rolled their own `useEffect → window.addEventListener('keydown')
// → if (e.key === 'Escape') close()` pattern.
//
// Behavior:
//   - Listens on `window` for `keydown` while `enabled` is true.
//   - On Escape: calls `e.stopPropagation()` then `handler()`.
//   - When `enabled` flips to false, the listener is removed.
//   - When `handler` identity changes, listener rebinds (fresh closure).
//
// Multi-panel coordination: each open panel registers its own handler. They
// all fire on ESC; per-panel `if (!isOpen) return` guards (or passing
// `enabled={isOpen}`) keep the side-effects scoped. Mutual-exclusion rules
// (e.g., R-1 panelReducer) ensure only one is open at a time, so in practice
// only one handler does work.
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
