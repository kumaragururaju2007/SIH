import React, { useState, useEffect, useRef } from 'react';
import { ChevronUp, ChevronDown, ArrowUpDown } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T, index: number) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (item: T) => string | number;
  onRowClick?: (item: T) => void;
  isLoading?: boolean;
  emptyMessage?: string;
  defaultSortKey?: string;
  defaultSortDir?: 'asc' | 'desc';
  className?: string;
}

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  onRowClick,
  isLoading = false,
  emptyMessage = 'No records found matching your filters.',
  defaultSortKey,
  defaultSortDir = 'asc',
  className = '',
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | undefined>(defaultSortKey);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(defaultSortDir);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const tableRef = useRef<HTMLTableElement>(null);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sortedData = React.useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a: any, b: any) => {
      let valA = a[sortKey];
      let valB = b[sortKey];

      if (valA === null || valA === undefined) valA = '';
      if (valB === null || valB === undefined) valB = '';

      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortDir === 'asc' ? valA - valB : valB - valA;
      }

      const strA = String(valA).toLowerCase();
      const strB = String(valB).toLowerCase();
      if (strA < strB) return sortDir === 'asc' ? -1 : 1;
      if (strA > strB) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, sortKey, sortDir]);

  // Keyboard navigation: Arrow Up, Arrow Down, Enter
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (sortedData.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < sortedData.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : sortedData.length - 1));
    } else if (e.key === 'Enter' && selectedIndex >= 0 && selectedIndex < sortedData.length) {
      e.preventDefault();
      onRowClick?.(sortedData[selectedIndex]);
    }
  };

  return (
    <div
      className={`w-full overflow-hidden rounded-lg border border-stoneBorder bg-surface shadow-sm focus:outline-none ${className}`}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      role="region"
      aria-label="Data Table with keyboard arrow navigation"
    >
      <div className="overflow-x-auto max-h-[680px]">
        <table ref={tableRef} className="w-full text-left text-xs border-collapse">
          {/* Sticky Header */}
          <thead className="sticky top-0 z-10 bg-stone-100 text-stone-700 font-semibold uppercase tracking-wider text-[11px] border-b border-stoneBorder">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`p-3 select-none ${col.className || ''}`}
                  scope="col"
                >
                  {col.sortable ? (
                    <button
                      onClick={() => handleSort(col.key)}
                      className="inline-flex items-center gap-1 font-semibold hover:text-primary transition-colors focus-visible:ring-1"
                    >
                      <span>{col.header}</span>
                      {sortKey === col.key ? (
                        sortDir === 'asc' ? (
                          <ChevronUp className="w-3.5 h-3.5 text-primary" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5 text-primary" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3 h-3 text-stone-400" />
                      )}
                    </button>
                  ) : (
                    <span>{col.header}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-stoneBorder bg-surface">
            {isLoading ? (
              // Loading Skeleton
              Array.from({ length: 5 }).map((_, rIdx) => (
                <tr key={rIdx} className="h-11">
                  {columns.map((_, cIdx) => (
                    <td key={cIdx} className="p-3">
                      <div className="h-4 bg-stone-200 rounded animate-pulse w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : sortedData.length === 0 ? (
              // Empty State
              <tr>
                <td colSpan={columns.length} className="p-8 text-center text-stone-500 text-xs">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              sortedData.map((item, rowIdx) => {
                const isSelected = rowIdx === selectedIndex;
                const key = keyExtractor(item);

                return (
                  <tr
                    key={key}
                    onClick={() => {
                      setSelectedIndex(rowIdx);
                      onRowClick?.(item);
                    }}
                    className={`h-11 transition-colors cursor-pointer select-none ${
                      isSelected
                        ? 'bg-amber-50/60 ring-1 ring-inset ring-accent'
                        : 'hover:bg-stone-50/80'
                    }`}
                    aria-selected={isSelected}
                  >
                    {columns.map((col) => (
                      <td key={col.key} className={`p-3 text-stone-800 ${col.className || ''}`}>
                        {col.render ? col.render(item, rowIdx) : (item as any)[col.key] || '—'}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
