import { WSClientEvent } from '@/app/(app)/chat/chatUtil';
import { Citation } from '@/app/(app)/chat/page';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type Status = { text: string; kind: '' | 'ok' | 'error' };

export function useChatSocket(opts: {
  wsUrl: string; // e.g. ws://localhost:8000/ws/chat
  onChatId?: (conversationId: number) => void;
  onAssistantDelta?: (requestId: string, delta: string) => void;
  onCitations?: (requestId: string, citations: Citation[]) => void;
  onDone?: (
    requestId: string,
    meta?: { message_id?: number; timing_ms?: number }
  ) => void;
  onError?: (detail: string) => void;
}) {
  const wsRef = useRef<WebSocket | null>(null);
  const [ready, setReady] = useState(false);

  const connect = useCallback(() => {
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const ws = new WebSocket(`${opts.wsUrl}?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => setReady(true);
    ws.onclose = () => setReady(false);
    ws.onerror = () => {
      setReady(false);
      opts.onError?.('WebSocket error');
    };

    ws.onmessage = (ev) => {
      let msg: any;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }

      switch (msg.type) {
        case 'chat_id':
          opts.onChatId?.(msg.conversation_id);
          break;
        case 'assistant_delta':
          opts.onAssistantDelta?.(msg.request_id, msg.delta);
          break;
        case 'assistant_citations':
          opts.onCitations?.(msg.request_id, msg.citations);
          break;
        case 'assistant_done':
          opts.onDone?.(msg.request_id, {
            message_id: msg.message_id,
            timing_ms: msg.timing_ms,
          });
          break;
        case 'error':
          opts.onError?.(msg.detail || 'Unknown error');
          break;
      }
    };
  }, [opts]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const send = useCallback((payload: WSClientEvent) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    ws.send(JSON.stringify(payload));
  }, []);

  return { ready, send, reconnect: connect };
}
