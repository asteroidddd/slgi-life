/**
 * Barrel export for base UI primitives.
 *
 * Usage:
 *   import { Button, Card, Badge, Score } from '@/components/ui';
 *   import type { ButtonVariant, BadgeVariant } from '@/components/ui';
 *
 * Add new primitives here as they are created. Feature components
 * (Map, AdongPanel, etc.) live under their own folders, NOT here.
 */

export { default as Button } from './Button';
export type { ButtonProps, ButtonVariant, ButtonSize } from './Button';

export { default as Card } from './Card';
export type { CardProps, CardVariant, CardPadding } from './Card';

export { default as Badge } from './Badge';
export type { BadgeProps, BadgeVariant, BadgeSize } from './Badge';

export { default as Chip } from './Chip';
export type { ChipProps } from './Chip';

export { default as Score } from './Score';
export type { ScoreProps, ScoreSize } from './Score';

export { default as Input } from './Input';
export type { InputProps } from './Input';

export { default as Select } from './Select';
export type { SelectProps } from './Select';

export { default as Slider } from './Slider';
export type { SliderProps } from './Slider';

export { default as MetricBar } from './MetricBar';
export type { MetricBarProps } from './MetricBar';

export { default as Modal } from './Modal';
export type { ModalProps } from './Modal';

export { default as Tooltip } from './Tooltip';
export type { TooltipProps, TooltipPlacement } from './Tooltip';

export { default as Gauge } from './Gauge';
export type { GaugeProps } from './Gauge';
