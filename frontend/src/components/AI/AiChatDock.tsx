import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import axios from 'axios';
import { Link, useLocation } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { useAuth } from '@/contexts/AuthContext';
import { getAIAPIKeys, getAgentDemoVisualization, postAgentQuery, unlockAIAPIKeys } from '@/lib/api';
import type {
  AgentQueryResponse,
  AgentVisualization,
  AgentVisualizationDatum,
  AIAPIKeyStatusResponse,
} from '@/types/api';

interface ChatMessage {
  id: number;
  role: 'user' | 'ai';
  text: string;
  data?: AgentQueryResponse;
  isError?: boolean;
  isLoading?: boolean;
}

let nextMessageId = 1;

const HIDDEN_PATHS = new Set(['/login', '/register']);
const VISIBLE_PATHS = new Set(['/', '/dashboard']);

export default function AiChatDock() {
  const location = useLocation();
  const { user, isLoading: authLoading } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  if (HIDDEN_PATHS.has(location.pathname) || !VISIBLE_PATHS.has(location.pathname)) return null;

  return (
    <>
      <button
        type="button"
        className="app-floating-button fixed bottom-5 right-5 z-[1300] h-11 no-underline"
        onClick={() => setIsOpen(true)}
        aria-haspopup="dialog"
      >
        AI에게 묻기
      </button>
      {isOpen ? (
        <AiChatDialog
          authLoading={authLoading}
          isAuthenticated={Boolean(user)}
          onClose={() => setIsOpen(false)}
        />
      ) : null}
    </>
  );
}

function AiChatDialog({
  authLoading,
  isAuthenticated,
  onClose,
}: {
  authLoading: boolean;
  isAuthenticated: boolean;
  onClose: () => void;
}) {
  const [keyStatus, setKeyStatus] = useState<AIAPIKeyStatusResponse | null>(null);
  const [keyStatusLoading, setKeyStatusLoading] = useState(false);
  const [keyStatusError, setKeyStatusError] = useState<string | null>(null);

  const refreshKeyStatus = useCallback(async () => {
    if (!isAuthenticated) return;
    setKeyStatusLoading(true);
    setKeyStatusError(null);
    try {
      setKeyStatus(await getAIAPIKeys());
    } catch (err) {
      setKeyStatusError(getErrorMessage(err, 'AI KEY 상태를 불러오지 못했습니다.'));
    } finally {
      setKeyStatusLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    void refreshKeyStatus();
  }, [refreshKeyStatus]);

  const hasConfiguredKey = keyStatus?.keys.some((key) => key.configured) ?? false;
  const hasUnlockedKey =
    keyStatus?.keys.some((key) => key.configured && key.unlocked) ?? false;

  return (
    <div
      className="fixed inset-0 z-[1400] flex items-end justify-end bg-black/20 p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label="AI 채팅"
    >
      <section className="flex h-[min(760px,calc(100vh-48px))] w-full max-w-[560px] flex-col overflow-hidden rounded-card border border-border bg-surface text-text shadow-2xl">
        <header className="flex items-center justify-between gap-3 border-b border-divider px-5 py-4">
          <div>
            <h2 className="m-0 text-card-heading font-semibold">자취맵 AI</h2>
            <p className="m-0 mt-1 text-[12px] leading-5 text-text-muted">
              동네, 월세, 시설, 교통 데이터를 같이 확인합니다.
            </p>
          </div>
          <button
            type="button"
            className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px] text-text-muted transition hover:text-text"
            onClick={onClose}
            aria-label="닫기"
          >
            ×
          </button>
        </header>

        {authLoading || keyStatusLoading ? (
          <GateMessage title="확인 중" message="AI 사용 가능 상태를 확인하고 있습니다." />
        ) : null}
        {!authLoading && !isAuthenticated ? (
          <GateMessage
            title="로그인이 필요합니다"
            message="AI 질의는 로그인 후 사용할 수 있습니다."
            action={<Link className="app-floating-button h-10 min-h-10 no-underline" to="/login">로그인하기</Link>}
          />
        ) : null}
        {!authLoading && isAuthenticated && keyStatusError ? (
          <GateMessage title="상태 확인 실패" message={keyStatusError} action={<GateButton onClick={refreshKeyStatus}>다시 시도</GateButton>} />
        ) : null}
        {!authLoading && isAuthenticated && keyStatus && !hasConfiguredKey ? (
          <GateMessage
            title="API KEY가 필요합니다"
            message="마이페이지에서 AI API KEY를 먼저 등록해주세요."
            action={<Link className="app-floating-button h-10 min-h-10 no-underline" to="/mypage">마이페이지로 이동</Link>}
          />
        ) : null}
        {!authLoading && isAuthenticated && keyStatus && hasConfiguredKey && !hasUnlockedKey ? (
          <UnlockGate onUnlocked={refreshKeyStatus} />
        ) : null}
        {!authLoading && isAuthenticated && keyStatus && hasUnlockedKey ? (
          <ChatWorkspace canUseDemo={Boolean(keyStatus.can_use_demo)} />
        ) : null}
      </section>
    </div>
  );
}

function GateMessage({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="grid max-w-[360px] gap-4 text-center">
        <div>
          <h3 className="m-0 text-card-heading font-semibold">{title}</h3>
          <p className="m-0 mt-2 text-[13px] leading-6 text-text-muted">{message}</p>
        </div>
        {action ? <div className="flex justify-center">{action}</div> : null}
      </div>
    </div>
  );
}

function GateButton({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="h-10 rounded-sm bg-primary px-4 text-[13px] font-semibold text-surface transition hover:bg-primary-hover"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function UnlockGate({ onUnlocked }: { onUnlocked: () => Promise<void> }) {
  const [passphrase, setPassphrase] = useState('');
  const [isUnlocking, setIsUnlocking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUnlock = async (event: FormEvent) => {
    event.preventDefault();
    if (!passphrase || isUnlocking) return;
    setIsUnlocking(true);
    setError(null);
    try {
      await unlockAIAPIKeys(passphrase);
      setPassphrase('');
      await onUnlocked();
    } catch (err) {
      setError(getErrorMessage(err, '복호화 문구가 맞지 않습니다.'));
    } finally {
      setIsUnlocking(false);
    }
  };

  return (
    <form className="flex flex-1 items-center justify-center p-6" onSubmit={handleUnlock}>
      <div className="grid w-full max-w-[360px] gap-4">
        <div className="text-center">
          <h3 className="m-0 text-card-heading font-semibold">API KEY 열기</h3>
          <p className="m-0 mt-2 text-[13px] leading-6 text-text-muted">
            저장된 AI API KEY를 사용하려면 복호화 문구를 입력해주세요.
          </p>
        </div>
        <label className="grid gap-2 text-caption text-text">
          복호화 문구
          <input
            type="password"
            value={passphrase}
            onChange={(event) => setPassphrase(event.target.value)}
            autoComplete="current-password"
            className="h-11 rounded-sm border border-border bg-surface-alt px-3 text-[15px] outline-none transition focus:border-primary"
          />
        </label>
        {error ? <p className="m-0 text-caption text-danger">{error}</p> : null}
        <button
          type="submit"
          disabled={!passphrase || isUnlocking}
          className="h-10 rounded-sm bg-primary px-4 text-[13px] font-semibold text-surface transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isUnlocking ? '여는 중...' : '30분 동안 열기'}
        </button>
        <Link className="text-center text-[12px] font-semibold text-primary hover:text-primary-hover" to="/mypage">
          API KEY 등록은 마이페이지에서 하기
        </Link>
      </div>
    </form>
  );
}

function ChatWorkspace({ canUseDemo }: { canUseDemo: boolean }) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 0,
      role: 'ai',
      text: '안녕하세요. 동네, 월세, 시설, 교통 조건을 물어보세요.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || isSending) return;

    const pendingId = nextMessageId++;
    setMessages((prev) => [
      ...prev,
      { id: nextMessageId++, role: 'user', text: question },
      { id: pendingId, role: 'ai', text: '답변을 준비 중입니다.', isLoading: true },
    ]);
    setInput('');
    setIsSending(true);

    try {
      const data = await postAgentQuery(question, conversationId);
      setConversationId(data.conversation_id);
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingId
            ? { id: pendingId, role: 'ai', text: data.answer, data }
            : message,
        ),
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingId
            ? {
                id: pendingId,
                role: 'ai',
                text: `답변을 불러오지 못했습니다. ${getErrorMessage(err, '잠시 후 다시 시도해주세요.')}`,
                isError: true,
              }
            : message,
        ),
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleDemoResponse = async () => {
    if (isSending) return;

    const pendingId = nextMessageId++;
    setMessages((prev) => [
      ...prev,
      { id: nextMessageId++, role: 'user', text: '테스트 응답 받기' },
      { id: pendingId, role: 'ai', text: '테스트 응답을 준비 중입니다.', isLoading: true },
    ]);
    setIsSending(true);

    try {
      const data = await getAgentDemoVisualization();
      setConversationId(data.conversation_id);
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingId
            ? { id: pendingId, role: 'ai', text: data.answer, data }
            : message,
        ),
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingId
            ? {
                id: pendingId,
                role: 'ai',
                text: `테스트 응답을 불러오지 못했습니다. ${getErrorMessage(err, '잠시 후 다시 시도해주세요.')}`,
                isError: true,
              }
            : message,
        ),
      );
    } finally {
      setIsSending(false);
    }
  };

  const startNewConversation = () => {
    setConversationId(undefined);
    setMessages([
      {
        id: nextMessageId++,
        role: 'ai',
        text: '새 대화를 시작합니다.',
      },
    ]);
  };

  return (
    <>
        <div className="flex items-center justify-between gap-3 border-b border-divider px-5 py-2">
        <span className="text-[12px] text-text-muted">
          {conversationId ? '대화 이어가는 중' : '새 대화'} · 창을 닫으면 현재 대화가 초기화됩니다.
        </span>
        <button
          type="button"
          className="h-8 rounded-sm bg-surface-alt px-3 text-[12px] font-semibold text-text-muted transition hover:text-text"
          onClick={startNewConversation}
        >
          새 대화
        </button>
        {canUseDemo ? (
          <button
            type="button"
            className="h-8 rounded-sm bg-primary px-3 text-[12px] font-semibold text-surface transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => void handleDemoResponse()}
            disabled={isSending}
          >
            테스트 응답 받기
          </button>
        ) : null}
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="grid gap-3">
          {messages.map((message) => (
            <ChatBubble key={message.id} message={message} />
          ))}
          <div ref={endRef} />
        </div>
      </div>
      <div className="border-t border-divider p-4">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.nativeEvent.isComposing) {
                event.preventDefault();
                void handleSend();
              }
            }}
            disabled={isSending}
            placeholder="예: 월세 낮고 카페 많은 동네 추천해줘"
            className="h-11 min-w-0 flex-1 rounded-sm border border-border bg-surface-alt px-3 text-[14px] outline-none transition placeholder:text-text-subtle focus:border-primary disabled:opacity-60"
          />
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={!input.trim() || isSending}
            className="h-11 rounded-sm bg-primary px-4 text-[13px] font-semibold text-surface transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSending ? '전송 중' : '전송'}
          </button>
        </div>
      </div>
    </>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[92%] rounded-card px-4 py-3 text-[13px] leading-6 shadow-sm ${
          isUser
            ? 'bg-primary text-surface'
            : message.isError
              ? 'bg-danger-soft text-danger'
              : 'bg-surface-alt text-text'
        }`}
      >
        {message.isLoading ? (
          <span className="mr-2 inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-r-transparent align-[-2px]" />
        ) : null}
        <div className="whitespace-pre-wrap break-words">{message.text}</div>
        {message.data ? <AgentResponseDetails data={message.data} /> : null}
      </div>
    </div>
  );
}

function AgentResponseDetails({ data }: { data: AgentQueryResponse }) {
  return (
    <div className="mt-3 grid gap-3 border-t border-divider pt-3">
      {data.neighborhoods.length > 0 ? (
        <div className="grid gap-2">
          {data.neighborhoods.map((item) => (
            <div key={`${item.rank}-${item.gu_name}-${item.ldong_name}`} className="rounded-sm bg-surface p-3">
              <div className="font-semibold">
                {item.rank}. {item.gu_name} {item.ldong_name}
              </div>
              <p className="m-0 mt-1 text-text-muted">{item.one_liner}</p>
              <p className="m-0 mt-1 text-text-subtle">{item.data_summary}</p>
            </div>
          ))}
        </div>
      ) : null}
      {data.visualizations.map((visualization, index) => (
        <AgentVisualizationRenderer
          key={`${visualization.title}-${index}`}
          visualization={visualization}
        />
      ))}
      {data.provider ? (
        <p className="m-0 text-[11px] text-text-subtle">
          {data.provider.used_provider}
          {data.provider.fallback_used ? ' fallback 사용' : ''}
        </p>
      ) : null}
    </div>
  );
}

function AgentVisualizationRenderer({ visualization }: { visualization: AgentVisualization }) {
  if (!visualization.data.length || visualization.type === 'none') return null;
  if (visualization.type === 'bar') return <AgentBarChart visualization={visualization} />;
  if (visualization.type === 'line') return <AgentLineChart visualization={visualization} />;
  if (visualization.type === 'table') return <AgentTable visualization={visualization} />;
  if (visualization.type === 'map') return <AgentMapList visualization={visualization} />;
  return <AgentTable visualization={visualization} />;
}

function AgentChartFrame({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-sm bg-surface p-3">
      <h4 className="m-0 mb-2 text-[13px] font-semibold text-text">{title}</h4>
      {children}
    </section>
  );
}

function AgentBarChart({ visualization }: { visualization: AgentVisualization }) {
  const data = chartData(visualization.data);
  return (
    <AgentChartFrame title={visualization.title}>
      <div className="h-[190px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: -18 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.35)" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value) => formatChartValue(value, visualization.unit)} />
            <Bar dataKey="value" fill="var(--color-primary, #2563eb)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </AgentChartFrame>
  );
}

function AgentLineChart({ visualization }: { visualization: AgentVisualization }) {
  const data = chartData(visualization.data);
  return (
    <AgentChartFrame title={visualization.title}>
      <div className="h-[190px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 10, bottom: 8, left: -18 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.35)" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={12} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value) => formatChartValue(value, visualization.unit)} />
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--color-primary, #2563eb)"
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </AgentChartFrame>
  );
}

function AgentTable({ visualization }: { visualization: AgentVisualization }) {
  const columns = useMemo(() => collectColumns(visualization.data), [visualization.data]);
  const rows = visualization.data.slice(0, 8);

  return (
    <AgentChartFrame title={visualization.title}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[360px] border-collapse text-left text-[12px]">
          <thead>
            <tr className="border-b border-divider text-text-muted">
              <th className="py-2 pr-3 font-semibold">항목</th>
              {columns.map((column) => (
                <th key={column} className="py-2 pr-3 font-semibold">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-divider last:border-b-0">
                <td className="py-2 pr-3 font-semibold text-text">{row.label}</td>
                {columns.map((column) => (
                  <td key={column} className="py-2 pr-3 text-text-muted">
                    {formatCell(row.columns?.[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {visualization.data.length > rows.length ? (
        <p className="m-0 mt-2 text-[11px] text-text-subtle">
          {visualization.data.length - rows.length}개 항목은 생략했습니다.
        </p>
      ) : null}
    </AgentChartFrame>
  );
}

function AgentMapList({ visualization }: { visualization: AgentVisualization }) {
  const points = visualization.data.filter(hasCoordinates);
  if (!points.length) return <AgentTable visualization={visualization} />;

  return (
    <AgentChartFrame title={visualization.title}>
      <div className="grid gap-2">
        {points.slice(0, 6).map((point) => (
          <div key={`${point.label}-${point.lat}-${point.lng}`} className="flex items-center justify-between gap-3 rounded-sm border border-border px-3 py-2">
            <div className="min-w-0">
              <div className="truncate font-semibold">{point.label}</div>
              <div className="text-[11px] text-text-subtle">
                {point.lat?.toFixed(5)}, {point.lng?.toFixed(5)}
              </div>
            </div>
            <Link
              className="shrink-0 text-[12px] font-semibold text-primary hover:text-primary-hover"
              to={`/?mode=plain&ai_lat=${point.lat}&ai_lng=${point.lng}&ai_label=${encodeURIComponent(point.label)}`}
            >
              지도에서 보기
            </Link>
          </div>
        ))}
      </div>
    </AgentChartFrame>
  );
}

function chartData(data: AgentVisualizationDatum[]) {
  return data
    .filter((item) => typeof item.value === 'number')
    .slice(0, 12)
    .map((item) => ({
      label: item.label,
      value: item.value,
      is_baseline: Boolean(item.is_baseline),
    }));
}

function collectColumns(data: AgentVisualizationDatum[]): string[] {
  const columns = new Set<string>();
  for (const row of data) {
    Object.keys(row.columns ?? {}).forEach((column) => columns.add(column));
  }
  if (columns.size === 0 && data.some((row) => row.value != null)) columns.add('값');
  return Array.from(columns);
}

function formatChartValue(value: unknown, unit: string) {
  if (typeof value !== 'number') return String(value ?? '-');
  return `${value.toLocaleString()}${unit ? ` ${unit}` : ''}`;
}

function formatCell(value: unknown) {
  if (value == null) return '-';
  if (typeof value === 'number') return value.toLocaleString();
  return String(value);
}

function hasCoordinates(item: AgentVisualizationDatum): item is AgentVisualizationDatum & { lat: number; lng: number } {
  if (typeof item.lat !== 'number' || typeof item.lng !== 'number') return false;
  if (!Number.isFinite(item.lat) || !Number.isFinite(item.lng)) return false;
  if (item.lat === 0 && item.lng === 0) return false;
  return item.lat >= 37.35 && item.lat <= 37.75 && item.lng >= 126.7 && item.lng <= 127.3;
}

function getErrorMessage(err: unknown, fallback: string) {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { error?: unknown; detail?: unknown } | undefined;
    if (typeof data?.detail === 'string' && data.detail) return data.detail;
    if (typeof data?.error === 'string' && data.error) return data.error;
    if (err.response?.status === 401) return 'API KEY를 다시 열어주세요.';
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
