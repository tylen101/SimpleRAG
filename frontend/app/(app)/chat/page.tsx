'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import styles from './ChatPage.module.css';
import ChatSettings from './ChatSettings/ChatSettings';
import ChatInput from './ChatInput/ChatInput';

export type ScopeMode = 'all' | 'selected';

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

export type Settings = {
  scopeMode: ScopeMode;
  doc_ids: number[];
  content: string;
  k_vec: number;
  k_text: number;
  use_text: boolean;
};

type SendMessageResponse = {
  answer?: string;
  message_id?: number | string;
  citations?: Citation[];
  detail?: string;
};

function uid(prefix = 'm') {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

export default function ChatPage() {
  const [settings, setSettings] = useState<Settings>({
    scopeMode: 'all',
    doc_ids: [],
    content: '',
    k_vec: 6,
    k_text: 6,
    use_text: false,
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<{
    text: string;
    kind?: 'ok' | 'error' | '';
  }>({
    text: '',
    kind: '',
  });
  const [isSending, setIsSending] = useState(false);
  const [timingMs, setTimingMs] = useState<number | null>(null);

  const conversationId = 0;

  async function sendMessage() {
    const content = (settings.content || '').trim();
    if (!content) {
      setStatus({ text: 'Please enter a message.', kind: 'error' });
      return;
    }

    if (settings.scopeMode === 'selected' && settings.doc_ids.length === 0) {
      setStatus({
        text: "Scope is 'selected' but no doc ids were provided.",
        kind: 'error',
      });
      return;
    }

    const payload = {
      content,
      scope: { mode: settings.scopeMode, doc_ids: settings.doc_ids },
      k_vec: Number(settings.k_vec),
      k_text: Number(settings.k_text),
      use_text: settings.use_text,
    };

    // optimistic user bubble
    const userMsg: ChatMessage = {
      id: uid('user'),
      role: 'user',
      content,
    };
    setMessages((prev) => [...prev, userMsg]);

    setStatus({ text: 'Sending...', kind: '' });
    setIsSending(true);
    setTimingMs(null);

    const t0 = performance.now();
    try {
      const res = await fetch(
        `http://localhost:8000/conversations/${conversationId}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload),
        }
      );

      const text = await res.text();
      let data: SendMessageResponse | { raw: string };
      try {
        data = JSON.parse(text);
      } catch {
        data = { raw: text };
      }

      if (!res.ok) {
        const detail =
          (data as SendMessageResponse)?.detail ||
          (data as any)?.raw ||
          text ||
          `HTTP ${res.status}`;

        setStatus({ text: `Error ${res.status}: ${detail}`, kind: 'error' });

        setMessages((prev) => [
          ...prev,
          {
            id: uid('err'),
            role: 'assistant',
            content: `ERROR: ${detail}`,
            meta: `HTTP ${res.status}`,
          },
        ]);
        return;
      }

      const t1 = performance.now();
      setTimingMs(Math.round(t1 - t0));

      const ok = data as SendMessageResponse;

      setMessages((prev) => [
        ...prev,
        {
          id: uid('asst'),
          role: 'assistant',
          content: ok.answer || '',
          citations: ok.citations || [],
          meta:
            ok.message_id != null ? `message_id=${ok.message_id}` : undefined,
        },
      ]);

      setStatus({ text: 'Done.', kind: 'ok' });

      // clear input content only (keep other settings)
      setSettings((s) => ({ ...s, content: '' }));
    } catch (e) {
      setStatus({ text: `Send failed: ${String(e)}`, kind: 'error' });
      setMessages((prev) => [
        ...prev,
        { id: uid('catch'), role: 'assistant', content: `ERROR: ${String(e)}` },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  const handleSendMessage = () => {
    // keeps your existing hook
    void sendMessage();
  };

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <h1 className={styles.title}>Chat</h1>
            <div className={styles.subtitle}>
              Create a conversation, send messages, see citations.
            </div>
          </div>

          <div className={styles.topbarRight}>
            <label className={styles.label} htmlFor="chatModel">
              Chat model: GPT-OSS:20B
            </label>
          </div>
        </header>

        <ChatSettings setSettings={setSettings} settings={settings} />
        {messages.map((msg) => {
          return <div key={msg.id}>{msg.content}</div>;
        })}

        <ChatInput
          value={settings.content}
          handleInput={(input) => {
            setSettings({ ...settings, content: input });
          }}
          placeholder="Ask a question..."
          disabled={isSending}
          onSend={handleSendMessage}
        />
      </div>
    </main>
  );
}
