import hashlib
from sqlalchemy.orm import Session
from models.Models import Document, DocumentVersion, DocumentBlob


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


class IngestionService:
    def create_document_with_version(
        self,
        db: Session,
        tenant_id: int,
        owner_user_id: int,
        filename: str | None,
        mime_type: str | None,
        title: str | None,
        file_bytes: bytes,
    ) -> tuple[Document, DocumentVersion]:
        digest = sha256_bytes(file_bytes)

        doc = Document(
            tenant_id=tenant_id,
            owner_user_id=owner_user_id,
            title=title or filename,
            filename=filename,
            mime_type=mime_type,
            sha256=digest,
            status="processing",
        )
        db.add(doc)
        db.flush()  # get doc_id

        version = DocumentVersion(
            doc_id=doc.doc_id,
            version_num=1,
            sha256=digest,
        )
        db.add(version)
        db.flush()  # get version_id

        blob = DocumentBlob(
            version_id=version.version_id,
            blob_data=file_bytes,
        )
        db.add(blob)

        db.commit()
        db.refresh(doc)
        db.refresh(version)
        return doc, version
