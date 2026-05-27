// AdongSelector — search-enabled combobox for selecting a adong.
//
// Loads the 426 adong list via useAdongScores, groups by gu, filters by
// adong name or gu name (Korean partial match). Keyboard navigable.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useAdongScores } from '@/hooks/useAdongs';
import type { AdongScore } from '@/types/api';
import { DEFAULT_WEIGHTS } from '@/types/api';

export interface AdongSelectorProps {
  /** Selected adong slug, or null if nothing selected. */
  value: string | null;
  /** Called when the user picks a adong. */
  onChange: (slug: string) => void;
  className?: string;
}

interface GuGroup {
  gu: string;
  adongs: AdongScore[];
}

export default function AdongSelector({
  value,
  onChange,
  className,
}: AdongSelectorProps) {
  const { data: adongs } = useAdongScores(DEFAULT_WEIGHTS);

  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Find the currently selected adong object
  const selectedAdong = useMemo(
    () => adongs?.find((d) => d.slug === value) ?? null,
    [adongs, value],
  );

  // Filter adongs by query (partial match on name or gu)
  const filtered = useMemo(() => {
    if (!adongs) return [];
    const q = query.trim().toLowerCase();
    if (!q) return adongs;
    return adongs.filter(
      (d) =>
        d.name.toLowerCase().includes(q) || d.gu.toLowerCase().includes(q),
    );
  }, [adongs, query]);

  // Group filtered adongs by gu
  const groups = useMemo<GuGroup[]>(() => {
    const map = new Map<string, AdongScore[]>();
    for (const d of filtered) {
      const list = map.get(d.gu);
      if (list) list.push(d);
      else map.set(d.gu, [d]);
    }
    return Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b, 'ko'))
      .map(([gu, adongs]) => ({ gu, adongs }));
  }, [filtered]);

  // Flat list of filtered adongs (for keyboard navigation indexing)
  const flatList = useMemo(
    () => groups.flatMap((g) => g.adongs),
    [groups],
  );

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Scroll active item into view
  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) return;
    const active = listRef.current.querySelector(
      `[data-index="${activeIndex}"]`,
    );
    active?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  const handleSelect = useCallback(
    (slug: string) => {
      onChange(slug);
      setIsOpen(false);
      setQuery('');
      setActiveIndex(-1);
    },
    [onChange],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) {
        if (e.key === 'ArrowDown' || e.key === 'Enter') {
          e.preventDefault();
          setIsOpen(true);
          setActiveIndex(0);
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setActiveIndex((prev) =>
            prev < flatList.length - 1 ? prev + 1 : 0,
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setActiveIndex((prev) =>
            prev > 0 ? prev - 1 : flatList.length - 1,
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (activeIndex >= 0 && activeIndex < flatList.length) {
            handleSelect(flatList[activeIndex].slug);
          }
          break;
        case 'Escape':
          e.preventDefault();
          setIsOpen(false);
          setActiveIndex(-1);
          break;
      }
    },
    [isOpen, activeIndex, flatList, handleSelect],
  );

  const displayValue = isOpen
    ? query
    : selectedAdong
      ? `${selectedAdong.gu} ${selectedAdong.name}`
      : '';

  const activeDescendant =
    activeIndex >= 0 && activeIndex < flatList.length
      ? `adong-option-${flatList[activeIndex].slug}`
      : undefined;

  return (
    <div
      ref={containerRef}
      className={`relative ${className ?? ''}`}
    >
      <div className="relative">
        {/* Search icon */}
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
          <path d="M11 11l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={isOpen}
          aria-activedescendant={activeDescendant}
          aria-controls="adong-selector-listbox"
          aria-label="동네 검색"
          placeholder="동네를 검색하세요"
          value={displayValue}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!isOpen) setIsOpen(true);
            setActiveIndex(0);
          }}
          onFocus={() => {
            setIsOpen(true);
            if (selectedAdong && !query) setQuery('');
          }}
          onKeyDown={handleKeyDown}
          className="w-full h-10 bg-surface border border-border rounded-sm pl-9 pr-3 text-caption text-text placeholder:text-text-subtle outline-none transition-colors duration-200 focus:border-focus-ring"
        />
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div
          id="adong-selector-listbox"
          ref={listRef}
          role="listbox"
          className="absolute top-full left-0 right-0 mt-1 max-h-[300px] overflow-y-auto bg-surface border border-border rounded-card shadow-floating z-50"
        >
          {groups.length === 0 && (
            <div className="px-4 py-6 text-center text-text-muted text-caption">
              검색 결과가 없습니다
            </div>
          )}
          {groups.map((group) => {
            return (
              <div key={group.gu}>
                <div className="sticky top-0 bg-surface-alt px-4 py-1.5 text-micro font-medium text-text-muted border-b border-border">
                  {group.gu}
                </div>
                {group.adongs.map((adong) => {
                  const flatIdx = flatList.indexOf(adong);
                  const isActive = flatIdx === activeIndex;
                  const isSelected = adong.slug === value;
                  return (
                    <div
                      key={adong.slug}
                      id={`adong-option-${adong.slug}`}
                      role="option"
                      data-index={flatIdx}
                      aria-selected={isSelected}
                      onClick={() => handleSelect(adong.slug)}
                      onMouseEnter={() => setActiveIndex(flatIdx)}
                      className={`px-4 py-2 text-caption cursor-pointer transition-colors duration-100 ${
                        isActive ? 'bg-surface-alt' : ''
                      } ${isSelected ? 'bg-primary-soft text-primary font-medium' : 'text-text'}`}
                    >
                      {adong.name}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
