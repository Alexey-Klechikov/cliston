import asyncio
import logging
from datetime import UTC, datetime

import aiosqlite
from config import DatabaseConfig
from services.sql.models import TacticalManual


class TacticsStorage:
    def __init__(self):
        self.db_path = str(DatabaseConfig.DB_PATH_GARM_INTELLIGENCE)

        asyncio.create_task(self._initialize())

    async def _initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tactical_manuals (
                    domain TEXT PRIMARY KEY,
                    objective TEXT,
                    manual TEXT,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP
                )
            """,
            )
            await db.commit()

    async def get_manuals(self, domain: str) -> list[TacticalManual]:
        domain = domain.lower().replace("www.", "").strip()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT objective, manual, success_count, failure_count, last_updated "
                "FROM tactical_manuals WHERE domain = ?",
                (domain,),
            ) as cursor:
                rows = await cursor.fetchall()
                manuals = [
                    TacticalManual(
                        domain=domain,
                        objective=row["objective"],
                        manual=row["manual"],
                        success_count=row["success_count"],
                        failure_count=row["failure_count"],
                        last_updated=datetime.fromisoformat(row["last_updated"]),
                    )
                    for row in rows
                ]

                logging.info(f"Retrieved {len(manuals)} Tactical manuals for domain '{domain}'.")
                return manuals

    async def archive_manual(self, manual: TacticalManual) -> None:
        """Save a newly drafted manual from Garm's infiltration."""

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO tactical_manuals
                (domain, objective, manual, last_updated, success_count, failure_count)
                VALUES (?, ?, ?, ?, 1, 0)
            """,
                (manual.domain, manual.objective, manual.manual, datetime.now(UTC).isoformat()),
            )

            await db.commit()
            logging.info(f"Tactical manual for {manual.domain} archived.")

    async def update_reliability(self, manual: TacticalManual, success: bool):
        """Adjudicate the outcome of a manual execution."""

        async with aiosqlite.connect(self.db_path) as db:
            field = ("success" if success else "failure") + "_count"

            await db.execute(
                f"""
                UPDATE tactical_manuals
                SET {field} = {field} + 1,
                    last_updated = ?
                WHERE domain = ? AND objective = ?
            """,
                (datetime.now(UTC).isoformat(), manual.domain, manual.objective),
            )

            await db.commit()
            logging.info(f"Tactical manual for {manual.domain} updated with a {'success' if success else 'failure'}.")
