from __future__ import annotations

import asyncio
import socket
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.db import SessionLocal
from core.config import settings
from services.ollama_client import OllamaClient
from services.embedding_service import EmbeddingService
from services.ingest_pipeline import IngestPipeline

# Claim one job atomically:
# - select next queued job
# - lock row SKIP LOCKED so multiple workers can run safely
# - update status to running + set lock metadata
PICK_SQL = text(
    """
SELECT job_id, tenant_id, doc_id
FROM document_jobs
WHERE status = 'queued'
  AND attempts < max_attempts
ORDER BY priority ASC, created_at ASC
FETCH FIRST 1 ROWS ONLY
"""
)

CLAIM_UPDATE_SQL = text(
    """
UPDATE document_jobs
SET status = 'running',
    locked_at = SYSTIMESTAMP,
    locked_by = :locked_by,
    updated_at = SYSTIMESTAMP,
    attempts = attempts + 1
WHERE job_id = :job_id
  AND status = 'queued'
  AND attempts < max_attempts
"""
)

MARK_SUCCESS_SQL = text(
    """
UPDATE document_jobs
SET status = 'succeeded',
    updated_at = SYSTIMESTAMP,
    last_error = NULL,
    locked_at = NULL,
    locked_by = NULL
WHERE job_id = :job_id
  AND status = 'running'
"""
)

MARK_FAILED_SQL = text(
    """
UPDATE document_jobs
SET status = 'failed',
    updated_at = SYSTIMESTAMP,
    last_error = :err,
    locked_at = NULL,
    locked_by = NULL
WHERE job_id = :job_id
  AND status = 'running'
"""
)

REQUEUE_SQL = text(
    """
UPDATE document_jobs
SET status = 'queued',
    updated_at = SYSTIMESTAMP,
    last_error = :err,
    locked_at = NULL,
    locked_by = NULL
WHERE job_id = :job_id
  AND status = 'running'
"""
)


class DocumentWorker:
    def __init__(self, poll_seconds: float = 2.0):
        self.poll_seconds = poll_seconds
        self._stop = asyncio.Event()
        self.worker_id = f"{socket.gethostname()}:{id(self)}"

        self.pipeline = IngestPipeline()
        self.ollama = OllamaClient(settings.OLLAMA_BASE_URL)
        self.embedding = EmbeddingService(self.ollama)

    def stop(self):
        self._stop.set()

    async def run_forever(self):
        print("running worker scan")
        while not self._stop.is_set():
            did_work = await self._try_process_one()
            if not did_work:
                await asyncio.sleep(self.poll_seconds)

    async def _try_process_one(self) -> bool:
        db: Session = SessionLocal()
        try:

            # Pick candidate
            row = db.execute(PICK_SQL).mappings().first()
            if not row:
                db.rollback()
                return False

            job_id = int(row["job_id"])
            tenant_id = int(row["tenant_id"])
            doc_id = int(row["doc_id"])
            # Attempt to claim atomically
            res = db.execute(
                CLAIM_UPDATE_SQL, {"job_id": job_id, "locked_by": self.worker_id}
            )
            print("res:", res)
            rowcount = getattr(res, "rowcount", None)
            print("claim update rowcount:", rowcount)

            if rowcount != 1:
                # Someone else grabbed it between pick and update
                db.rollback()
                return True  # did "work" (we raced), loop again immediately

            db.commit()
            dbg = db.execute(
                text(
                    "SELECT status, attempts, locked_by FROM document_jobs WHERE job_id=:id"
                ),
                {"id": job_id},
            ).first()
            print("claimed job state:", dbg)

        except Exception as e:
            import traceback

            print("CLAIM FAILED:", repr(e))
            traceback.print_exc()
            db.rollback()
            return False
        finally:
            db.close()

        # process outside claim transaction...
        db2: Session = SessionLocal()
        try:
            result = await self.pipeline.process_document(
                db=db2,
                tenant_id=tenant_id,
                doc_id=doc_id,
                embedding_service=self.embedding,
                max_chars=5000,
            )
            print("pipeline result:", result)

            if result["status"] == "ready":
                db2.execute(MARK_SUCCESS_SQL, {"job_id": job_id})
                db2.commit()
            else:
                err = result.get("error") or "Unknown failure"
                # retry until attempts >= max_attempts
                # (attempts was already incremented when marked running)
                # Decide to requeue or fail by checking attempts in DB
                attempts_row = (
                    db2.execute(
                        text(
                            "SELECT attempts, max_attempts FROM document_jobs WHERE job_id = :job_id"
                        ),
                        {"job_id": job_id},
                    )
                    .mappings()
                    .first()
                )

                if attempts_row and int(attempts_row["attempts"]) < int(
                    attempts_row["max_attempts"]
                ):
                    db2.execute(REQUEUE_SQL, {"job_id": job_id, "err": err})
                else:
                    db2.execute(MARK_FAILED_SQL, {"job_id": job_id, "err": err})
                db2.commit()

            return True

        except Exception as e:
            import traceback

            print("PROCESS FAILED:", repr(e))
            traceback.print_exc()
            db2.rollback()
            # On unexpected crash, mark failed (or requeue—up to you)
            db2.execute(MARK_FAILED_SQL, {"job_id": job_id, "err": str(e)})
            db2.commit()
            return True
        finally:
            db2.close()
