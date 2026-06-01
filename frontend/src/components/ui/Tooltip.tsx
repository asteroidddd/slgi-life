import { useId } from 'react';
import type { ReactElement, ReactNode } from 'react';

export type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right';

export interface TooltipProps {
  label: ReactNode;
  placement?: TooltipPlacement;
  children: ReactElement;
}

const placementClasses: Record<TooltipPlacement, string> = {
  top: 'bottom-[calc(100%+8px)] left-1/2 -translate-x-1/2 translate-y-0.5 group-hover:-translate-x-1/2 group-hover:translate-y-0 group-focus-within:-translate-x-1/2 group-focus-within:translate-y-0',
  bottom: 'top-[calc(100%+8px)] left-1/2 -translate-x-1/2 -translate-y-0.5 group-hover:-translate-x-1/2 group-hover:translate-y-0 group-focus-within:-translate-x-1/2 group-focus-within:translate-y-0',
  left: 'right-[calc(100%+8px)] top-1/2 translate-x-0.5 -translate-y-1/2 group-hover:translate-x-0 group-hover:-translate-y-1/2 group-focus-within:translate-x-0 group-focus-within:-translate-y-1/2',
  right: 'left-[calc(100%+8px)] top-1/2 -translate-x-0.5 -translate-y-1/2 group-hover:translate-x-0 group-hover:-translate-y-1/2 group-focus-within:translate-x-0 group-focus-within:-translate-y-1/2',
};

function Tooltip({ label, placement = 'top', children }: TooltipProps) {
  const id = useId();
  return (
    <span className="relative inline-flex group">
      <span
        className="inline-flex"
        aria-describedby={id}
      >
        {children}
      </span>
      <span
        id={id}
        role="tooltip"
        className={`pointer-events-none absolute z-[1100] max-w-60 whitespace-pre-line rounded-xs bg-[var(--secondary-overlay-bg)] px-3 py-2 text-micro font-normal leading-[1.4] tracking-normal text-surface opacity-0 shadow-lg backdrop-blur-md transition-all duration-[120ms] ease-out group-hover:opacity-100 group-focus-within:opacity-100 ${placementClasses[placement]}`}
      >
        {label}
      </span>
    </span>
  );
}

export default Tooltip;
