from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from models.Models import DocumentJob, DocumentVersion


class JobService:
    def enqueue_ingest(self, db: Session, tenant_id: int, doc_id: int) -> DocumentJob:
        # Attach latest version_id (optional but useful)
        print("running the document job with ", doc_id)
        ver = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.doc_id == doc_id)
            .order_by(DocumentVersion.version_num.desc())
            .first()
        )

        print("version ", ver)

        job = DocumentJob(
            tenant_id=tenant_id,
            doc_id=doc_id,
            version_id=ver.version_id if ver else None,
            status="queued",
            priority=100,
            attempts=0,
            max_attempts=3,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_job(self, db: Session, tenant_id: int, job_id: int) -> DocumentJob | None:
        return (
            db.query(DocumentJob)
            .filter(DocumentJob.job_id == job_id, DocumentJob.tenant_id == tenant_id)
            .first()
        )
