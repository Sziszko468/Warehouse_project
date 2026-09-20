import csv
import io
from collections.abc import Iterable

from fastapi.responses import StreamingResponse

# Not real pagination - a pragmatic upper bound so a single export call can't try to stream an
# unbounded number of rows.
EXPORT_ROW_LIMIT = 10_000


def csv_response(filename: str, header: list[str], rows: Iterable[list]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
