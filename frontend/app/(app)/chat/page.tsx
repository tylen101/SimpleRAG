'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import styles from './ChatPage.module.css';
import ChatSettings from './ChatSettings/ChatSettings';
import ChatInput from './ChatInput/ChatInput';

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
  const handleSendMessage = () => {
    console.log('send message');
  };

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        {/* <div>CHAT</div> */}

        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <h1 className={styles.title}>Chat</h1>
            <div className={styles.subtitle}>
              Create a conversation, send messages, see citations.
            </div>
          </div>

          <div className={styles.topbarRight}>
            {/* <span className={styles.pill}>
              <span className={styles.pillDot} />
              Draft mode (/chat)
            </span> */}
            <label className={styles.label} htmlFor="chatModel">
              Chat model: GPT-OSS:20B
            </label>
            {/* <input
              id="chatModel"
              className={styles.input}
              // value={chatModel}
              // onChange={(e) => setChatModel(e.target.value)}
              placeholder="leave empty to use default"
            /> */}
          </div>
        </header>

        {/* Settings */}
        <ChatSettings />
        {/*  chat settings and filters */}
        {/* collapsable */}
        {/*  existing chat messages  OR begin chat */}

        {/* if existing chat, show input at bottom */}

        <ChatInput
          placeholder="Ask a question..."
          disabled={false}
          onSend={handleSendMessage}
        />
      </div>
    </main>
  );
}
