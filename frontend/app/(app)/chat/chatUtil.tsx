import { Citation } from './page';

export type WSClientEvent = {
  type: 'user_message';
  request_id: string; // client-generated id for correlation
  conversation_id: number; // 0 means "create new"
  content: string;
  scope: { mode: 'all' | 'selected'; doc_ids: number[] };
  k_vec: number;
  k_text: number;
  use_text: boolean;
};

export type WSServerEvent =
  | {
      type: 'chat_id';
      request_id: string;
      conversation_id: number; // newly created or same as provided
      title?: string;
    }
  | {
      type: 'assistant_start';
      request_id: string;
      assistant_message_id: string; // client-side id or server-side handle
    }
  | {
      type: 'assistant_delta';
      request_id: string;
      delta: string; // token chunk
    }
  | {
      type: 'assistant_citations';
      request_id: string;
      citations: Citation[];
    }
  | {
      type: 'assistant_done';
      request_id: string;
      message_id?: number; // DB message id (final)
      timing_ms?: number;
    }
  | {
      type: 'error';
      request_id?: string;
      detail: string;
      code?: string;
    };
