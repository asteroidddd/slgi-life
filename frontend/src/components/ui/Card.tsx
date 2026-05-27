import { forwardRef } from 'react';
import type { ElementType, HTMLAttributes, ReactNode } from 'react';

export type CardVariant = 'default' | 'inset';
export type CardPadding = 'none' | 'md' | 'lg';

export interface CardProps extends HTMLAttributes<HTMLElement> {
  variant?: CardVariant;
  padding?: CardPadding;
  as?: ElementType;
  children?: ReactNode;
}

const variantClasses: Record<CardVariant, string> = {
  default: 'bg-surface border-border',
  inset: 'bg-surface-alt border-transparent',
};

const paddingClasses: Record<CardPadding, string> = {
  none: 'p-0',
  md: 'p-4',
  lg: 'p-5',
};

const Card = forwardRef<HTMLElement, CardProps>(function Card(
  { variant = 'default', padding = 'md', as, className, children, ...rest },
  ref
) {
  const Tag = (as ?? 'div') as ElementType;
  const classes = [
    'border border-solid rounded-card',
    variantClasses[variant],
    paddingClasses[padding],
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Tag ref={ref} className={classes} {...rest}>
      {children}
    </Tag>
  );
});

export default Card;
