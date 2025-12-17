'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import styles from './ChatPage.module.css';

type ScopeMode = 'all' | 'selected';

type Citation = {
  doc_id: number;
  chunk_id: number;
  page_start?: number | null;
  page_end?: number | null;
  section_path?: string | null;
  score: number;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  meta?: string;
  citations?: Citation[];
};

type ChunkOut = {
  doc_id: number;
  chunk_id: number;
  page_start?: number | null;
  page_end?: number | null;
  section_path?: string | null;
  chunk_text: string;
};

function parseDocIds(input: string): number[] {
  const s = (input || '').trim();
  if (!s) return [];
  return s
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => Number(x))
    .filter((n) => Number.isFinite(n) && n > 0);
}

function pagesLabel(c: {
  page_start?: number | null;
  page_end?: number | null;
}) {
  if (c.page_start == null) return '';
  const end =
    c.page_end != null && c.page_end !== c.page_start ? `-${c.page_end}` : '';
  return `p${c.page_start}${end}`;
}

export default function ChatPage() {
  // -----------------------
  // UI state (draft-mode page)
  // -----------------------
  const [chatModel, setChatModel] = useState<string>('');
  const [conversationId, setConversationId] = useState<string>('');
  const [scopeMode, setScopeMode] = useState<ScopeMode>('all');
  const [docIdsRaw, setDocIdsRaw] = useState<string>('');
  const [kVec, setKVec] = useState<number>(8);
  const [kText, setKText] = useState<number>(6);
  const [useText, setUseText] = useState<boolean>(true);

  const [message, setMessage] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<{
    kind: 'idle' | 'ok' | 'error';
    text: string;
  }>({
    kind: 'idle',
    text: '',
  });
  const [timing, setTiming] = useState<string>('');
  const [busy, setBusy] = useState<boolean>(false);

  // Source modal state
  const [sourceOpen, setSourceOpen] = useState<boolean>(false);
  const [sourceLoading, setSourceLoading] = useState<boolean>(false);
  const [sourceMeta, setSourceMeta] = useState<string>('');
  const [sourceTitle, setSourceTitle] = useState<string>('Source');
  const [sourceText, setSourceText] = useState<string>('');

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const docIds = useMemo(() => parseDocIds(docIdsRaw), [docIdsRaw]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length]);

  function setOk(text: string) {
    setStatus({ kind: 'ok', text });
  }
  function setError(text: string) {
    setStatus({ kind: 'error', text });
  }
  function clearStatus() {
    setStatus({ kind: 'idle', text: '' });
  }

  async function createConversation() {
    setBusy(true);
    clearStatus();
    setTiming('');
    try {
      const payload = {
        chat_model_id: chatModel.trim() ? chatModel.trim() : null,
        title: null,
      };

      const res = await fetch('https://localhost:8080/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const text = await res.text();
      const data = safeJson(text);

      if (!res.ok) {
        setError(`Error ${res.status}: ${data?.detail || text}`);
        return;
      }

      setConversationId(String(data.conversation_id));
      setOk(`Conversation created: ${data.conversation_id}`);
    } catch (e) {
      setError(`Create failed: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage() {
    clearStatus();
    setTiming('');

    const cid = Number(conversationId);
    if (!Number.isFinite(cid) || cid <= 0) {
      setError('Please create or enter a valid conversation id.');
      return;
    }

    const content = message.trim();
    if (!content) {
      setError('Please enter a message.');
      return;
    }

    if (scopeMode === 'selected' && docIds.length === 0) {
      setError("Scope is 'selected' but no doc ids were provided.");
      return;
    }

    const payload = {
      content,
      scope: { mode: scopeMode, doc_ids: docIds },
      k_vec: kVec || 8,
      k_text: kText || 6,
      use_text: useText,
    };

    // optimistic user bubble
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
    };
    setMessages((prev) => [...prev, userMsg]);
    setBusy(true);

    const t0 = performance.now();
    try {
      const res = await fetch(
        `https://localhost:8080/conversations/${cid}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload),
        }
      );

      const text = await res.text();
      const data = safeJson(text);

      if (!res.ok) {
        setError(`Error ${res.status}: ${data?.detail || text}`);
        const errMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `ERROR: ${data?.detail || text}`,
          meta: `HTTP ${res.status}`,
        };
        setMessages((prev) => [...prev, errMsg]);
        return;
      }

      const t1 = performance.now();
      setTiming(`(${Math.round(t1 - t0)} ms)`);

      const asstMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: String(data.answer ?? ''),
        meta:
          data.message_id != null ? `message_id=${data.message_id}` : undefined,
        citations: Array.isArray(data.citations) ? data.citations : [],
      };

      setMessages((prev) => [...prev, asstMsg]);
      setMessage('');
      setOk('Done.');
    } catch (e) {
      setError(`Send failed: ${String(e)}`);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `ERROR: ${String(e)}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function fetchChunk(
    chunkId: number,
    maxChars = 6000
  ): Promise<ChunkOut | null> {
    const res = await fetch('https://localhost:8080/chunks/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ chunk_ids: [chunkId], max_chars: maxChars }),
    });

    const text = await res.text();
    const data = safeJson(text);

    if (!res.ok) throw new Error(data?.detail || text);
    if (!Array.isArray(data) || data.length === 0) return null;
    return data[0] as ChunkOut;
  }

  async function showSource(c: Citation) {
    clearStatus();
    setSourceOpen(true);
    setSourceLoading(true);

    try {
      const chunk = await fetchChunk(c.chunk_id, 6000);
      if (!chunk) {
        setError('Source not found (maybe not in your tenant).');
        setSourceOpen(false);
        return;
      }

      const header = `[${chunk.doc_id}:${chunk.chunk_id}]`;
      setSourceTitle(header);

      const meta =
        [pagesLabel(chunk), chunk.section_path || '']
          .filter(Boolean)
          .join(' • ') || '—';
      setSourceMeta(meta);
      setSourceText(chunk.chunk_text || '');

      setOk('Loaded source.');
      setTimeout(() => clearStatus(), 800);
    } catch (e) {
      setError(`Source fetch failed: ${String(e)}`);
    } finally {
      setSourceLoading(false);
    }
  }

  async function copyToClipboard(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setOk('Copied.');
      setTimeout(() => clearStatus(), 900);
    } catch {
      setError('Clipboard copy failed (browser permissions).');
    }
  }

  function clearUI() {
    setMessages([]);
    setTiming('');
    clearStatus();
  }

  function onMessageKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      void sendMessage();
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <h1 className={styles.title}>RAG Chat</h1>
            <div className={styles.subtitle}>
              Create a conversation, send messages, see citations.
            </div>
          </div>

          <div className={styles.topbarRight}>
            <span className={styles.pill}>
              <span className={styles.pillDot} />
              Draft mode (/chat)
            </span>
          </div>
        </header>

        {/* Settings */}
        <section className={styles.card}>
          <div className={styles.formRow}>
            <label className={styles.label} htmlFor="chatModel">
              Chat model (for new conversation)
            </label>
            <input
              id="chatModel"
              className={styles.input}
              value={chatModel}
              onChange={(e) => setChatModel(e.target.value)}
              placeholder="leave empty to use server default"
            />
            <div className={styles.helpText}>
              Used only when creating a new conversation.
            </div>
          </div>

          <div className={styles.grid2}>
            <div className={styles.formRow}>
              <label className={styles.label} htmlFor="conversationId">
                Conversation ID
              </label>
              <input
                id="conversationId"
                className={styles.input}
                value={conversationId}
                onChange={(e) => setConversationId(e.target.value)}
                placeholder="Click Create New or paste an id"
                inputMode="numeric"
              />
            </div>

            <div className={styles.actions}>
              <button
                className={styles.button}
                type="button"
                onClick={() => void createConversation()}
                disabled={busy}
              >
                Create New Conversation
              </button>
              <button
                className={styles.buttonSecondary}
                type="button"
                onClick={clearUI}
                disabled={busy}
              >
                Clear UI
              </button>
            </div>
          </div>

          {status.text ? (
            <div
              className={[
                styles.status,
                status.kind === 'error' ? styles.statusError : '',
                status.kind === 'ok' ? styles.statusOk : '',
              ].join(' ')}
            >
              {status.text}
            </div>
          ) : null}
        </section>

        {/* Composer */}
        <section className={styles.card}>
          <div className={styles.grid2}>
            <div className={styles.formRow}>
              <label className={styles.label} htmlFor="scopeMode">
                Scope
              </label>
              <select
                id="scopeMode"
                className={styles.select}
                value={scopeMode}
                onChange={(e) => setScopeMode(e.target.value as ScopeMode)}
              >
                <option value="all">all</option>
                <option value="selected">selected</option>
              </select>
            </div>

            <div className={styles.formRow}>
              <label className={styles.label} htmlFor="docIds">
                Doc IDs (when scope=selected)
              </label>
              <input
                id="docIds"
                className={styles.input}
                value={docIdsRaw}
                onChange={(e) => setDocIdsRaw(e.target.value)}
                placeholder="e.g. 101, 102"
              />
            </div>
          </div>

          <div className={styles.grid4}>
            <div className={styles.formRow}>
              <label className={styles.label} htmlFor="kVec">
                k_vec
              </label>
              <input
                id="kVec"
                className={styles.input}
                type="number"
                min={1}
                max={50}
                value={kVec}
                onChange={(e) => setKVec(Number(e.target.value))}
              />
            </div>

            <div className={styles.formRow}>
              <label className={styles.label} htmlFor="kText">
                k_text
              </label>
              <input
                id="kText"
                className={styles.input}
                type="number"
                min={1}
                max={50}
                value={kText}
                onChange={(e) => setKText(Number(e.target.value))}
              />
            </div>

            <div className={styles.formRow}>
              <label className={styles.label} htmlFor="useText">
                use_text
              </label>
              <select
                id="useText"
                className={styles.select}
                value={String(useText)}
                onChange={(e) => setUseText(e.target.value === 'true')}
              >
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            </div>

            <div className={styles.formRow}>
              <label className={styles.label}>&nbsp;</label>
              <div className={styles.actionsInline}>
                <button
                  className={styles.button}
                  type="button"
                  onClick={() => void sendMessage()}
                  disabled={busy}
                >
                  Send
                </button>
              </div>
            </div>
          </div>

          <label className={styles.label} htmlFor="message">
            Message
          </label>
          <textarea
            id="message"
            className={styles.textarea}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={onMessageKeyDown}
            placeholder="Ask a question... (Ctrl+Enter to send)"
          />

          <div className={styles.timing}>{timing}</div>
        </section>

        {/* Transcript */}
        <section className={styles.card}>
          <div className={styles.transcriptHeader}>
            <div className={styles.badge}>Transcript</div>
            <div className={styles.small}>{messages.length} messages</div>
          </div>

          <div className={styles.chat}>
            {messages.map((m) => (
              <div
                key={m.id}
                className={[
                  styles.bubble,
                  m.role === 'user'
                    ? styles.bubbleUser
                    : styles.bubbleAssistant,
                ].join(' ')}
              >
                <div className={styles.bubbleHeader}>
                  <div className={styles.bubbleRole}>
                    {m.role === 'user' ? 'USER' : 'ASSISTANT'}
                  </div>
                  <div className={styles.small}>{m.meta || ''}</div>
                </div>

                <div className={styles.bubbleContent}>{m.content}</div>

                {m.role === 'assistant' && m.citations && m.citations.length ? (
                  <div className={styles.citations}>
                    {m.citations.map((c) => {
                      const handle = `[${c.doc_id}:${c.chunk_id}]`;
                      return (
                        <div
                          key={`${c.doc_id}:${c.chunk_id}:${c.score}`}
                          className={styles.cite}
                          role="button"
                          tabIndex={0}
                          onClick={() => void showSource(c)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ')
                              void showSource(c);
                          }}
                          title="Open source"
                        >
                          <span className={styles.badgeSmall}>{handle}</span>
                          <span className={styles.citeMeta}>
                            {pagesLabel(c)}
                          </span>
                          <span className={styles.small}>
                            score:{Number(c.score).toFixed(4)}
                          </span>
                          <button
                            className={styles.chipButton}
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              void copyToClipboard(handle);
                            }}
                          >
                            Copy
                          </button>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
        </section>
      </div>

      {/* Source Modal */}
      {sourceOpen ? (
        <div
          className={styles.modalBackdrop}
          role="dialog"
          aria-modal="true"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSourceOpen(false);
          }}
        >
          <div className={styles.modalCard}>
            <div className={styles.modalTop}>
              <div>
                <div className={styles.small}>{sourceMeta}</div>
                <div className={styles.modalTitle}>{sourceTitle}</div>
              </div>

              <div className={styles.actions}>
                <button
                  className={styles.buttonSecondary}
                  type="button"
                  onClick={() => void copyToClipboard(sourceText)}
                  disabled={sourceLoading || !sourceText}
                >
                  Copy text
                </button>
                <button
                  className={styles.button}
                  type="button"
                  onClick={() => setSourceOpen(false)}
                >
                  Close
                </button>
              </div>
            </div>

            <div className={styles.modalBody}>
              <pre className={styles.sourcePre}>
                {sourceLoading ? 'Loading…' : sourceText}
              </pre>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

function safeJson(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
