import { t } from "../../i18n/strings";
import { Button } from "./Button";

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
}

export function Pagination({ total, limit, offset, onOffsetChange }: PaginationProps) {
  if (total <= limit) return null;

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="pagination">
      <span>
        {currentPage}. {t.page} {t.of} {totalPages}
      </span>
      <Button variant="ghost" size="sm" disabled={offset === 0} onClick={() => onOffsetChange(Math.max(0, offset - limit))}>
        {t.previous}
      </Button>
      <Button variant="ghost" size="sm" disabled={offset + limit >= total} onClick={() => onOffsetChange(offset + limit)}>
        {t.next}
      </Button>
    </div>
  );
}
