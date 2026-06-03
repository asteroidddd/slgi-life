import { forwardRef } from 'react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'filled' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3',
  md: 'h-10 px-5',
  lg: 'h-12 px-6',
};

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-surface border-primary rounded-md min-h-[44px] px-6 hover:enabled:bg-primary-hover hover:enabled:border-primary-hover',
  secondary:
    'bg-transparent text-text border-transparent underline underline-offset-[3px] decoration-1 rounded-xs px-0 h-auto hover:enabled:text-link',
  outline:
    'bg-transparent text-text border-primary rounded-xl hover:enabled:bg-primary-soft',
  filled:
    'bg-primary text-surface border-primary rounded-xl hover:enabled:bg-primary-hover hover:enabled:border-primary-hover',
  ghost:
    'bg-transparent text-text border-transparent rounded-sm hover:enabled:bg-primary-soft hover:enabled:text-primary',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    fullWidth = false,
    leftIcon,
    rightIcon,
    disabled,
    className,
    children,
    type = 'button',
    ...rest
  },
  ref
) {
  const isPrimarySm = variant === 'primary' && size === 'sm';

  const classes = [
    'inline-flex items-center justify-center gap-2 font-base text-button leading-[1.4] font-semibold tracking-normal whitespace-nowrap cursor-pointer select-none border border-solid transition-all duration-[120ms] ease-out',
    variantClasses[variant],
    variant !== 'primary' && variant !== 'secondary' ? sizeClasses[size] : '',
    variant === 'primary' && size !== 'sm' ? sizeClasses[size] : '',
    isPrimarySm ? 'min-h-8 h-8 px-4' : '',
    fullWidth ? 'w-full' : '',
    fullWidth && variant === 'secondary' ? 'min-h-[44px]' : '',
    loading ? 'opacity-80' : '',
    'disabled:cursor-not-allowed disabled:opacity-100 disabled:bg-disabled disabled:text-surface disabled:border-disabled',
    'focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      ref={ref}
      type={type}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && (
        <span
          className="w-3.5 h-3.5 rounded-full border-2 border-current border-r-transparent shrink-0 [animation:ui-button-spin_700ms_linear_infinite]"
          aria-hidden="true"
        />
      )}
      {!loading && leftIcon && (
        <span className="inline-flex items-center justify-center w-[1em] h-[1em] text-[1.1em] shrink-0 [&>svg]:w-full [&>svg]:h-full" aria-hidden="true">
          {leftIcon}
        </span>
      )}
      <span className="inline-flex items-center">{children}</span>
      {!loading && rightIcon && (
        <span className="inline-flex items-center justify-center w-[1em] h-[1em] text-[1.1em] shrink-0 [&>svg]:w-full [&>svg]:h-full" aria-hidden="true">
          {rightIcon}
        </span>
      )}
    </button>
  );
});

export default Button;
