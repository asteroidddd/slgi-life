// AiPanelContext — controls the global AI side panel open/close state.
//
// Usage:
//   <AiPanelProvider>
//     <AppContent />   {/* reads isOpen for layout shift */}
//     <AiSidePanel />  {/* reads isOpen + close for the panel itself */}
//   </AiPanelProvider>
//
//   const { isOpen, open, close, toggle } = useAiPanel();

import { createContext, useContext, useMemo, useState, useCallback } from 'react';
import type { ReactNode } from 'react';

interface AiPanelContextValue {
  isOpen: boolean;
  open(): void;
  close(): void;
  toggle(): void;
}

const AiPanelContext = createContext<AiPanelContextValue | undefined>(undefined);

export function AiPanelProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);
  const value = useMemo(
    () => ({ isOpen, open, close, toggle }),
    [isOpen, open, close, toggle],
  );
  return (
    <AiPanelContext.Provider value={value}>{children}</AiPanelContext.Provider>
  );
}

export function useAiPanel(): AiPanelContextValue {
  const ctx = useContext(AiPanelContext);
  if (!ctx) throw new Error('useAiPanel must be used within AiPanelProvider');
  return ctx;
}
