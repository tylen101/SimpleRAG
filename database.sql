  CREATE TABLE tenants (
  tenant_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        VARCHAR2(200) NOT NULL,
  created_at  TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE app_users (
  user_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id   NUMBER NOT NULL REFERENCES tenants(tenant_id),
  email       VARCHAR2(320),
  display_name VARCHAR2(200),
  created_at  TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE documents (
  doc_id         NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id      NUMBER NOT NULL REFERENCES tenants(tenant_id),
  owner_user_id  NUMBER NOT NULL REFERENCES app_users(user_id),
  title          VARCHAR2(500),
  filename       VARCHAR2(500),
  mime_type      VARCHAR2(200),
  sha256         VARCHAR2(64) NOT NULL,
  status         VARCHAR2(30) CHECK (status IN ('uploaded','processing','ready','failed')),
  created_at     TIMESTAMP DEFAULT SYSTIMESTAMP,
  updated_at     TIMESTAMP
);


CREATE TABLE document_blobs (
  version_id NUMBER
    CONSTRAINT pk_document_blobs
      PRIMARY KEY,
  blob_data  BLOB,

  CONSTRAINT fk_docblobs_version
    FOREIGN KEY (version_id)
    REFERENCES document_versions(version_id)
    ON DELETE CASCADE
);

CREATE TABLE document_text (
  version_id NUMBER
    CONSTRAINT pk_document_text
      PRIMARY KEY,
  extracted_text CLOB,
  structure_json CLOB,
  created_at     TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,

  CONSTRAINT fk_doctext_version
    FOREIGN KEY (version_id)
    REFERENCES document_versions(version_id)
    ON DELETE CASCADE
);


CREATE TABLE document_versions (
  version_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  doc_id         NUMBER NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  version_num    NUMBER NOT NULL,
  sha256         VARCHAR2(64) NOT NULL,
  created_at     TIMESTAMP DEFAULT SYSTIMESTAMP,
  CONSTRAINT uq_doc_version UNIQUE (doc_id, version_num)
);

CREATE TABLE document_chunks (
  chunk_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  version_id   NUMBER NOT NULL REFERENCES document_versions(version_id) ON DELETE CASCADE,
  doc_id       NUMBER NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  tenant_id    NUMBER NOT NULL REFERENCES tenants(tenant_id),

  chunk_index  NUMBER NOT NULL,
  page_start   NUMBER,
  page_end     NUMBER,
  section_path VARCHAR2(2000),
  token_count  NUMBER,
  chunk_text   CLOB NOT NULL,

  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP,
  CONSTRAINT uq_chunk UNIQUE (version_id, chunk_index)
);

CREATE TABLE document_jobs (
  job_id        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id     NUMBER NOT NULL REFERENCES tenants(tenant_id),
  doc_id        NUMBER NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  version_id    NUMBER REFERENCES document_versions(version_id) ON DELETE SET NULL,

  status        VARCHAR2(20) NOT NULL
                CHECK (status IN ('queued','running','succeeded','failed','canceled')),

  priority      NUMBER DEFAULT 100 NOT NULL,
  attempts      NUMBER DEFAULT 0 NOT NULL,
  max_attempts  NUMBER DEFAULT 3 NOT NULL,

  locked_at     TIMESTAMP,
  locked_by     VARCHAR2(200),

  last_error    CLOB,
  created_at    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  updated_at    TIMESTAMP
);

CREATE INDEX idx_doc_jobs_status_pri
  ON document_jobs(status, priority, created_at);

CREATE INDEX idx_doc_jobs_doc
  ON document_jobs(doc_id);

CREATE INDEX idx_doc_jobs_tenant
  ON document_jobs(tenant_id);


CREATE TABLE chunk_embeddings (
  chunk_id           NUMBER PRIMARY KEY REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
  tenant_id          NUMBER NOT NULL REFERENCES tenants(tenant_id),
  embedding_model_id VARCHAR2(200) NOT NULL,
  embedding_dim      NUMBER NOT NULL,
  embedding          VECTOR(4096, FLOAT32) NOT NULL,
  created_at         TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE VECTOR INDEX chunk_emb_hnsw_idx
  ON chunk_embeddings (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH;

CREATE INDEX chunk_text_ctx_idx
  ON document_chunks(chunk_text)
  INDEXTYPE IS CTXSYS.CONTEXT;

CREATE TABLE conversations (
  conversation_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id       NUMBER NOT NULL REFERENCES tenants(tenant_id),
  user_id         NUMBER NOT NULL REFERENCES app_users(user_id),
  chat_model_id   VARCHAR2(200) NOT NULL,
  title           VARCHAR2(500),
  created_at      TIMESTAMP DEFAULT SYSTIMESTAMP,
  updated_at      TIMESTAMP
);

CREATE TABLE messages (
  message_id      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  conversation_id NUMBER NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
  role            VARCHAR2(20) CHECK (role IN ('user','assistant','system')),
  content         CLOB NOT NULL,
  created_at      TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE message_citations (
  citation_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

  message_id     NUMBER NOT NULL
    REFERENCES messages(message_id) ON DELETE CASCADE,

  doc_id         NUMBER NOT NULL
    REFERENCES documents(doc_id) ON DELETE CASCADE,

  chunk_id       NUMBER NOT NULL
    REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,

  page_start     NUMBER,
  page_end       NUMBER,
  section_path   VARCHAR2(2000),

  score          NUMBER,
  created_at     TIMESTAMP DEFAULT SYSTIMESTAMP,

  CONSTRAINT uq_message_chunk UNIQUE (message_id, chunk_id)
);

CREATE INDEX ix_msgcit_message ON message_citations(message_id);
CREATE INDEX ix_msgcit_doc ON message_citations(doc_id);
CREATE INDEX ix_msgcit_chunk ON message_citations(chunk_id);


CREATE TABLE retrieval_events (
  event_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  message_id   NUMBER NOT NULL REFERENCES messages(message_id) ON DELETE CASCADE,
  query_text   CLOB NOT NULL,
  filters_json CLOB,
  results_json CLOB,
  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP
);

