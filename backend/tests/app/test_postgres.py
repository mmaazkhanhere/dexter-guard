from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.postgres import PostgresSourceRepository
from source_ingestion.contracts import SourceDocument


def test_saved_example_batch_uses_a_cursor_for_executemany() -> None:
    repository = PostgresSourceRepository("postgresql://synthetic.invalid/db")
    database = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    database.transaction.return_value.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    repository._database = database

    document = SourceDocument(
        source_id="synthetic-source-001",
        source_version=1,
        resident_test_id="synthetic-resident-001",
        language="de-DE",
        transcript_text="Die Bewohnerin berichtet guten Schlaf.",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    repository.ensure_initial([document])

    cursor.executemany.assert_called_once()
    connection.executemany.assert_not_called()
