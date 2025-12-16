import React, { useMemo, useState } from 'react';
import styles from './Table.module.css';

export type ColumnDef<T extends Record<string, any>> = {
  title: string;
  key: keyof T | string;
  logic?: (row: T) => React.ReactNode; // executed on each row
  sortable?: boolean;
};

type SortDir = 'asc' | 'desc';

export type TableProps<T extends Record<string, any>> = {
  data: T[];
  columns: ColumnDef<T>[];
  loading?: boolean;
  rowKey?: keyof T | ((row: T, index: number) => string | number);
  emptyText?: string;
  className?: string;
  skeletonRows?: number;
};

function getValue<T extends Record<string, any>>(row: T, key: string) {
  // supports dot paths like "user.name"
  if (!key.includes('.')) return (row as any)[key];
  return key
    .split('.')
    .reduce((acc: any, part) => (acc == null ? acc : acc[part]), row);
}

function normalizeForSort(v: any): {
  type: 'num' | 'str' | 'empty';
  value: number | string;
} {
  if (v == null) return { type: 'empty', value: '' };
  if (typeof v === 'number' && Number.isFinite(v))
    return { type: 'num', value: v };
  if (typeof v === 'boolean') return { type: 'num', value: v ? 1 : 0 };
  if (v instanceof Date) return { type: 'num', value: v.getTime() };
  const s = String(v).trim();
  if (!s) return { type: 'empty', value: '' };

  // If it looks like a number, sort as number
  const maybe = Number(s.replace(/,/g, ''));
  if (!Number.isNaN(maybe) && Number.isFinite(maybe))
    return { type: 'num', value: maybe };

  return { type: 'str', value: s.toLowerCase() };
}

export function Table<T extends Record<string, any>>(props: TableProps<T>) {
  const {
    data,
    columns,
    loading = false,
    rowKey,
    emptyText = 'No results found.',
    className,
    skeletonRows = 6,
  } = props;

  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const sortableKeys = useMemo(() => {
    const set = new Set<string>();
    columns.forEach((c) => c.sortable && set.add(String(c.key)));
    return set;
  }, [columns]);

  const sorted = useMemo(() => {
    if (!sortKey || !sortableKeys.has(sortKey)) return data;

    const copy = [...data];
    copy.sort((a, b) => {
      const av = normalizeForSort(getValue(a, sortKey));
      const bv = normalizeForSort(getValue(b, sortKey));

      // empty always last
      if (av.type === 'empty' && bv.type !== 'empty') return 1;
      if (bv.type === 'empty' && av.type !== 'empty') return -1;
      if (av.type === 'empty' && bv.type === 'empty') return 0;

      // numbers before strings (stable-ish behavior)
      if (av.type !== bv.type) return av.type === 'num' ? -1 : 1;

      if (av.type === 'num' && bv.type === 'num') {
        return (av.value as number) - (bv.value as number);
      }
      return (av.value as string).localeCompare(bv.value as string);
    });

    return sortDir === 'asc' ? copy : copy.reverse();
  }, [data, sortKey, sortDir, sortableKeys]);

  function onHeaderClick(col: ColumnDef<T>) {
    if (!col.sortable) return;
    const key = String(col.key);
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir('asc');
      return;
    }
    setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
  }

  function getRowId(row: T, index: number) {
    if (!rowKey) return index;
    if (typeof rowKey === 'function') return rowKey(row, index);
    return String((row as any)[rowKey] ?? index);
  }

  return (
    <div className={`${styles.dtWrap} ${className ?? ''}`}>
      <div className={styles.dtCard}>
        <div
          className={`${styles.dtTableScroll} ${
            loading ? styles.isLoading : ''
          }`}
        >
          <table className={styles.dtTable} role="table">
            <thead>
              <tr>
                {columns.map((col) => {
                  const key = String(col.key);
                  const isSorted = sortKey === key;
                  const canSort = !!col.sortable;

                  return (
                    <th
                      key={key}
                      className={`${styles.dtTh} ${
                        canSort ? styles.isSortable : ''
                      }`}
                      onClick={() => onHeaderClick(col)}
                      aria-sort={
                        !canSort
                          ? 'none'
                          : isSorted
                          ? sortDir === 'asc'
                            ? 'ascending'
                            : 'descending'
                          : 'none'
                      }
                      scope="col"
                    >
                      <span className={styles.dtThInner}>
                        <span className={styles.dtThTitle}>{col.title}</span>

                        {canSort && (
                          <span
                            className={`${styles.dtSortIcon} ${
                              isSorted ? styles.isActive : ''
                            }`}
                            aria-hidden="true"
                          >
                            <span
                              className={`${styles.dtCaret} ${styles.up} ${
                                isSorted && sortDir === 'asc' ? styles.on : ''
                              }`}
                            />
                            <span
                              className={`${styles.dtCaret} ${styles.down} ${
                                isSorted && sortDir === 'desc' ? styles.on : ''
                              }`}
                            />
                          </span>
                        )}
                      </span>
                    </th>
                  );
                })}
              </tr>
            </thead>

            <tbody>
              {loading ? (
                Array.from({ length: skeletonRows }).map((_, i) => (
                  <tr key={`sk-${i}`} className={styles.dtTr}>
                    {columns.map((c) => (
                      <td key={`${String(c.key)}-${i}`} className={styles.dtTd}>
                        <div className={styles.dtSkel} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : sorted.length === 0 ? (
                <tr className={styles.dtTr}>
                  <td
                    className={`${styles.dtTd} ${styles.dtEmpty}`}
                    colSpan={columns.length}
                  >
                    {emptyText}
                  </td>
                </tr>
              ) : (
                sorted.map((row, idx) => (
                  <tr key={getRowId(row, idx)} className={styles.dtTr}>
                    {columns.map((col) => {
                      const k = String(col.key);
                      const content = col.logic
                        ? col.logic(row)
                        : (getValue(row, k) as any);

                      return (
                        <td key={k} className={styles.dtTd}>
                          {content ?? <span className={styles.dtMuted}>—</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* subtle bottom edge */}
        <div className={styles.dtFooterBar} />
      </div>
    </div>
  );
}
