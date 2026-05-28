// AiSidePanel — slide-in AI chat shell.
//
// Fixed position, slides from the right. ESC to close.

import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';

import { useAiPanel } from '@/contexts/AiPanelContext';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { postAgentQuery } from '@/lib/api';
import type { AgentQueryResponse } from '@/types/api';

interface Message {
  id: number;
  role: 'ai' | 'user';
  text: string;
  data?: AgentQueryResponse;
  isError?: boolean;
  isLoading?: boolean;
}

const WELCOME_MESSAGE: Message = {
  id: 0,
  role: 'ai',
  text: '안녕하세요! 자취맵 AI입니다. 동네에 대해 궁금한 것을 물어보세요.',
};

let nextId = 1;

export default function AiSidePanel() {
  const { isOpen, close } = useAiPanel();
  const location = useLocation();
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEscapeKey(close, isOpen);

  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

  useEffect(() => {
    if (isAuthPage && isOpen) close();
  }, [isAuthPage, isOpen, close]);

  const scrollToBottom = useCallback(() => {
    // Small delay so DOM updates before scroll
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isSending) return;


    const userMsg: Message = { id: nextId++, role: 'user', text };
    const pendingId = nextId++;
    const pendingMsg: Message = {
      id: pendingId,
      role: 'ai',
      text: '답변을 준비 중이에요.',
      isLoading: true,
    };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setInput('');
    setIsSending(true);
    scrollToBottom();

    try {
      const data = await postAgentQuery(text);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === pendingId
            ? { id: pendingId, role: 'ai', text: data.answer, data }
            : msg,
        ),
      );
    } catch (err) {
      const message = getAgentErrorMessage(err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === pendingId
            ? {
                id: pendingId,
                role: 'ai',
                text: `답변을 불러오지 못했습니다. ${message}`,
                isError: true,
              }
            : msg,
        ),
      );
    } finally {
      setIsSending(false);
      scrollToBottom();
    }
  }, [input, isSending, scrollToBottom]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  if (isAuthPage) return null;

  return (
    <aside
      className={`fixed top-[var(--space-14)] right-0 bottom-0 w-[400px] bg-surface border-l border-divider z-[999] flex flex-col transition-transform duration-500 ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
      style={{ transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)' }}
      aria-label="AI 채팅 패널"
      aria-hidden={!isOpen}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-divider shrink-0">
        <h2 className="text-body-large font-semibold text-text">자취맵 AI</h2>
        <button
          type="button"
          className="w-8 h-8 rounded-md border border-transparent bg-transparent text-text-muted text-feature-heading leading-none cursor-pointer shrink-0 transition-colors duration-[120ms] ease-out inline-flex items-center justify-center hover:bg-surface-alt hover:text-text focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
          aria-label="AI 패널 닫기"
          onClick={close}
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3" aria-live="polite">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2.5 rounded-card text-caption leading-relaxed whitespace-pre-wrap break-words ${
                msg.role === 'user'
                  ? 'bg-primary text-surface'
                  : msg.isError
                    ? 'bg-danger-soft text-danger'
                    : 'bg-surface-alt text-text'
              }`}
              role={msg.isError ? 'alert' : msg.isLoading ? 'status' : undefined}
            >
              {msg.isLoading && (
                <span
                  className="inline-block w-3 h-3 mr-2 rounded-full border-2 border-current border-r-transparent align-[-2px] [animation:ui-button-spin_700ms_linear_infinite]"
                  aria-hidden="true"
                />
              )}
              {msg.text}
              {msg.data ? <AgentResultSummary data={msg.data} /> : null}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-divider px-5 py-3 shrink-0">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSending}
            placeholder="메시지를 입력하세요..."
            className="flex-1 h-10 bg-surface-alt border border-border rounded-pill px-4 text-caption text-text placeholder:text-text-subtle outline-none transition-colors duration-200 focus:border-focus-ring disabled:cursor-not-allowed disabled:opacity-70"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-primary text-surface shrink-0 transition-colors duration-200 hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="메시지 보내기"
            aria-busy={isSending || undefined}
          >
            {isSending ? (
              <span
                className="w-4 h-4 rounded-full border-2 border-current border-r-transparent [animation:ui-button-spin_700ms_linear_infinite]"
                aria-hidden="true"
              />
            ) : (
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M14 2L7 9M14 2l-4.5 12-2-5.5L2 6.5 14 2z"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
      </div>
    </aside>
  );
}

function AgentResultSummary({ data }: { data: AgentQueryResponse }) {
  if (data.neighborhoods.length === 0 && data.visualizations.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-divider pt-3">
      {data.neighborhoods.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {data.neighborhoods.map((item) => (
            <div
              key={`${item.rank}-${item.gu_name}-${item.ldong_name}`}
              className="rounded-sm bg-surface px-3 py-2"
            >
              <div className="font-semibold text-text">
                {item.rank}. {item.gu_name} {item.ldong_name}
              </div>
              <div className="mt-1 text-text-muted">{item.one_liner}</div>
              <div className="mt-1 text-text-subtle">{item.data_summary}</div>
            </div>
          ))}
        </div>
      )}
      {data.visualizations.map((viz, idx) => (
        <div key={`${viz.title}-${idx}`} className="rounded-sm bg-surface px-3 py-2">
          <div className="font-semibold text-text">{viz.title}</div>
          <div className="mt-1 flex flex-col gap-1 text-text-muted">
            {viz.data.slice(0, 4).map((datum) => (
              <div key={datum.label} className="flex justify-between gap-3">
                <span className="truncate">{datum.label}</span>
                <span className="shrink-0 tabular">
                  {datum.value != null
                    ? `${datum.value}${viz.unit ? ` ${viz.unit}` : ''}`
                    : formatColumns(datum.columns)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function formatColumns(columns: AgentQueryResponse['visualizations'][number]['data'][number]['columns']) {
  if (!columns) return '';
  return Object.entries(columns)
    .slice(0, 2)
    .map(([key, value]) => `${key}: ${value ?? '-'}`)
    .join(' · ');
}

function getAgentErrorMessage(err: unknown) {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as
      | { error?: unknown; detail?: unknown }
      | undefined;

    if (typeof data?.error === 'string' && data.error.length > 0) {
      return data.error;
    }
    if (typeof data?.detail === 'string' && data.detail.length > 0) {
      return data.detail;
    }
    if (err.response?.status === undefined || err.response.status === 0) {
      return '백엔드 연결을 확인해주세요.';
    }
  }

  if (err instanceof Error && err.message.length > 0) {
    return err.message;
  }

  return '잠시 후 다시 시도해주세요.';
}
