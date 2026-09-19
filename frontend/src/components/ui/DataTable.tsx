import type { ReactNode } from "react";
import { t } from "../../i18n/strings";
import { ArchiveIcon } from "./icons";
import { GearSpinner } from "./GearSpinner";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  numeric?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  isLoading?: boolean;
  emptyMessage?: string;
}

export function DataTable<T>({ columns, rows, rowKey, isLoading, emptyMessage }: DataTableProps<T>) {
  if (isLoading) {
    return <GearSpinner label={t.loading} />;
  }

  if (rows.length === 0) {
    return (
      <div className="empty-state">
        <ArchiveIcon />
        <div>{emptyMessage ?? t.noResults}</div>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.numeric ? "num" : undefined}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((col) => (
                <td key={col.key} className={col.numeric ? "num" : undefined}>
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
