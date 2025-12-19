'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import styles from './ChatPage.module.css';
import ChatSettings from './ChatSettings/ChatSettings';
import ChatInput from './ChatInput/ChatInput';
import { useChatSocket } from '@/hooks/useChatSocket';

export type ScopeMode = 'all' | 'selected';

export type Citation = {
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
  const [conversationId, setConversationId] = useState<number>(0);
  const chatSocket = useChatSocket({
    wsUrl: 'ws://localhost:8000/ws/chat',
    onChatId: (newId) => {
      // update local state
      setConversationId(newId);

      // optional: update route instantly
      // router.replace(`/chat/${newId}`);
    },
    onAssistantDelta: (requestId, delta) => {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === requestId ? { ...m, content: (m.content || '') + delta } : m
        )
      );
    },
    onCitations: (requestId, citations) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === requestId ? { ...m, citations } : m))
      );
    },
    onDone: (requestId, meta) => {
      if (meta?.timing_ms != null) setTimingMs(Math.round(meta.timing_ms));
      setMessages((prev) =>
        prev.map((m) =>
          m.id === requestId
            ? {
                ...m,
                meta:
                  meta?.message_id != null
                    ? `message_id=${meta.message_id}`
                    : 'Done.',
              }
            : m
        )
      );
      setStatus({ text: 'Done.', kind: 'ok' });
      setIsSending(false);
    },
    onError: (detail) => {
      setStatus({ text: `Error: ${detail}`, kind: 'error' });
      setIsSending(false);
    },
  });

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

  function newRequestId() {
    return `${Date.now()}_${Math.random().toString(16).slice(2)}`;
  }

  async function sendMessageWS() {
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

    const requestId = newRequestId();

    // optimistic user bubble
    setMessages((prev) => [
      ...prev,
      { id: uid('user'), role: 'user', content },
      // create an assistant bubble immediately; we’ll stream into it
      {
        id: requestId,
        role: 'assistant',
        content: '',
        meta: 'streaming…',
        citations: [],
      },
    ]);

    setStatus({ text: 'Sending...', kind: '' });
    setIsSending(true);
    setTimingMs(null);

    try {
      chatSocket.send({
        type: 'user_message',
        request_id: requestId,
        conversation_id: conversationId, // can be 0
        content,
        scope: { mode: settings.scopeMode, doc_ids: settings.doc_ids },
        k_vec: Number(settings.k_vec),
        k_text: Number(settings.k_text),
        use_text: settings.use_text,
      });
    } catch (e) {
      setStatus({ text: `Send failed: ${String(e)}`, kind: 'error' });
      setIsSending(false);
      return;
    }
  }

  const handleSendMessage = () => {
    sendMessage();
    setSettings((s) => ({ ...s, content: '' }));
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
