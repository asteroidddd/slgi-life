import { useCallback, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import type { ReactNode } from 'react';

import { useEscapeKey } from '@/hooks/useEscapeKey';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  ariaLabel?: string;
  ariaLabelledBy?: string;
  maxWidth?: number;
  dismissOnBackdrop?: boolean;
  dismissOnEsc?: boolean;
  hideCloseButton?: boolean;
  children: ReactNode;
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function Modal({
  open,
  onClose,
  title,
  ariaLabel,
  ariaLabelledBy,
  maxWidth = 600,
  dismissOnBackdrop = true,
  dismissOnEsc = true,
  hideCloseButton = false,
  children,
}: ModalProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEscapeKey(onClose, open && dismissOnEsc);

  useEffect(() => {
    if (!open) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = original;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    const t = window.setTimeout(() => {
      if (!cardRef.current) return;
      const firstFocusable = cardRef.current.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      (firstFocusable ?? cardRef.current).focus();
    }, 0);
    return () => {
      window.clearTimeout(t);
      previouslyFocused.current?.focus?.();
    };
  }, [open]);

  const onCardKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'Tab' || !cardRef.current) return;
    const focusables = Array.from(
      cardRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
    ).filter((el) => !el.hasAttribute('disabled'));
    if (focusables.length === 0) {
      e.preventDefault();
      cardRef.current.focus();
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement as HTMLElement | null;
    if (e.shiftKey && active === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault();
      first.focus();
    }
  }, []);

  if (!open) return null;
  if (typeof document === 'undefined') return null;

  const labelledBy =
    ariaLabelledBy ??
    (typeof title === 'string' && title.length > 0 ? 'ui-modal-title' : undefined);
  const computedAriaLabel =
    !labelledBy && (ariaLabel ?? (typeof title === 'string' ? title : undefined));

  return createPortal(
    <div
      className="fixed inset-0 bg-backdrop flex items-center justify-center p-4 z-[1000] [animation:ui-modal-fade-in_200ms_ease-out]"
      onClick={dismissOnBackdrop ? onClose : undefined}
      role="presentation"
    >
      <div
        ref={cardRef}
        className="relative w-full bg-surface rounded-card border border-divider flex flex-col max-h-[calc(100vh-32px)] overflow-hidden z-[1010] shadow-floating [animation:ui-modal-pop-in_200ms_ease-out] outline-none focus-visible:outline-none"
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-label={computedAriaLabel || undefined}
        style={{ maxWidth }}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onCardKeyDown}
      >
        {(title || !hideCloseButton) && (
          <div className="flex items-center justify-between gap-3 px-6 pt-6 pb-3">
            {title && (
              <h2 id="ui-modal-title" className="text-feature-heading font-semibold leading-[1.3] tracking-normal text-text m-0">
                {title}
              </h2>
            )}
            {!hideCloseButton && (
              <button
                type="button"
                className="inline-flex items-center justify-center w-8 h-8 rounded-sm text-text-muted cursor-pointer shrink-0 transition-all duration-[120ms] ease-out hover:bg-surface-alt hover:text-text focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
                onClick={onClose}
                aria-label="닫기"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M4 4L12 12M12 4L4 12"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            )}
          </div>
        )}
        <div className="px-6 pt-3 pb-6 overflow-y-auto">{children}</div>
      </div>
    </div>,
    document.body
  );
}

export default Modal;
