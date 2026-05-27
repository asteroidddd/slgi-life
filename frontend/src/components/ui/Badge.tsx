import type { HTMLAttributes, ReactNode } from 'react';

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'
  | 'category'
  | 'mono';
export type BadgeSize = 'sm' | 'md';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
  children: ReactNode;
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'bg-success-soft text-success rounded-full',
  warning: 'bg-warning-soft text-accent rounded-full',
  danger: 'bg-danger-soft text-danger rounded-full',
  info: 'bg-info-soft text-info rounded-full',
  neutral: 'bg-surface-alt text-text-muted rounded-full',
  category:
    'bg-accent text-surface rounded-[22px] px-2.5 py-1 h-auto font-medium tracking-normal',
  mono:
    'bg-transparent text-text-subtle border-divider rounded-xs px-2 py-0.5 font-mono text-mono-label leading-[1.4] tracking-[0.26px] uppercase h-auto',
};

// sm/md typography uses the Pretendard `caption` token (14px, normal case,
// 0 tracking). `mono` variant keeps the legacy uppercase + 0.26px tracking
// look — those mono artifacts are intentional only for that variant.
const sizeClasses: Record<BadgeSize, string> = {
  sm: 'text-caption',
  md: 'text-caption h-auto px-3 py-1',
};

function Badge({
  variant = 'neutral',
  size = 'sm',
  className,
  children,
  ...rest
}: BadgeProps) {
  const isSpecial = variant === 'category' || variant === 'mono';

  const classes = [
    'inline-flex items-center justify-center gap-1 font-normal tracking-normal whitespace-nowrap leading-none border border-solid border-transparent',
    isSpecial ? '' : `h-[22px] px-2 py-[3px]`,
    variantClasses[variant],
    isSpecial ? '' : sizeClasses[size],
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span className={classes} {...rest}>
      {children}
    </span>
  );
}

export default Badge;
