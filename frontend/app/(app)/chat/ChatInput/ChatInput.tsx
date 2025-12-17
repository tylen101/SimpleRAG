'use client';

import { useEffect, useRef } from 'react';
import styles from './ChatInput.module.css';

interface ChatInputProps {
  handleInput: (value: string) => void;
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  value: string;
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Message…',
  handleInput,
  value,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;

    onSend(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={styles.wrapper}>
      <div
        className={styles.inputContainer}
        onClick={
          // Focus textarea when clicking on the input container
          () => {
            textareaRef.current?.focus();
          }
        }
      >
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          rows={1}
          value={value}
          onChange={(e) => handleInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
        />

        <button
          className={styles.sendButton}
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          aria-label="Send message"
        >
          ➤
        </button>
      </div>

      <div className={styles.hint}>
        <span>Enter</span> to send · <span>Shift + Enter</span> for newline
      </div>
    </div>
  );
}
