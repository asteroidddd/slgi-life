import type { ButtonHTMLAttributes } from 'react';

export interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
}

export default function Chip({
  active = false,
  className,
  children,
  ...rest
}: ChipProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={`min-h-[44px] py-2 px-4 border rounded-full text-caption cursor-pointer transition-all duration-[120ms] ease-out ${
        active
          ? 'bg-surface-alt border-text text-text font-medium'
          : 'bg-surface border-divider text-text-subtle hover:border-text-subtle hover:text-text hover:bg-surface-alt'
      } disabled:opacity-50 disabled:cursor-not-allowed${className ? ` ${className}` : ''}`}
      {...rest}
    >
      {children}
    </button>
  );
}
