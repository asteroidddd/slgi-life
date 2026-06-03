import { useTheme } from '@/features/common/contexts/ThemeContext';
import Tooltip from '@/features/common/components/ui/Tooltip';

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.75v2.5M12 18.75v2.5M4.22 4.22l1.77 1.77M18.01 18.01l1.77 1.77M2.75 12h2.5M18.75 12h2.5M4.22 19.78l1.77-1.77M18.01 5.99l1.77-1.77" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20.25 14.32A7.75 7.75 0 0 1 9.68 3.75 8.5 8.5 0 1 0 20.25 14.32Z" />
    </svg>
  );
}

export default function ThemeToggle({ className = '' }: { className?: string }) {
  const { isDark, toggleTheme } = useTheme();
  const label = isDark ? '라이트 모드로 전환' : '다크 모드로 전환';

  return (
    <Tooltip label={label} placement="bottom">
      <button
        type="button"
        className={`theme-toggle ${className}`}
        aria-label={label}
        onClick={toggleTheme}
      >
        {isDark ? <MoonIcon /> : <SunIcon />}
      </button>
    </Tooltip>
  );
}
