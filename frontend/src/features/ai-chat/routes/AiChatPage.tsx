import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import axios from 'axios';
import { Link, useSearchParams } from 'react-router-dom';
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

import { useAuth } from '@/features/common/contexts/AuthContext';
import { useAdongScores } from '@/features/common/hooks/useAdongs';
import { getAIAPIKeys, getAgentDemoVisualization, postAgentQuery, unlockAIAPIKeys } from '@/features/common/lib/api';
import { DEFAULT_WEIGHTS } from '@/features/common/types/api';
import { loadCandidateRegions } from '@/features/candidates/lib/candidates';
import HeatMap from '@/features/map/components/HeatMap';
import type {
  AgentQueryResponse,
  AgentVisualization,
  AgentVisualizationDatum,
  AIAPIKeyStatusResponse,
} from '@/features/common/types/api';

interface ChatMessage {
  id: number;
  role: 'user' | 'ai';
  text: string;
  data?: AgentQueryResponse;
  isError?: boolean;
  isLoading?: boolean;
}

let nextMessageId = 1;

const AI_AGENT_PUBLIC_MODE = import.meta.env.VITE_AI_AGENT_PUBLIC_MODE === 'true';

function formatCandidateScore(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
  return Math.round(value).toString();
}

function buildCandidateComparePrompt() {
  const candidates = loadCandidateRegions();
  if (candidates.length === 0) return '';
  const lines = candidates.map((candidate, index) => {
    const level = candidate.regionLevel === 'adong' ? '행정동' : '법정동';
    return `${index + 1}. ${candidate.gu} ${candidate.name} (${level}) - 부동산 ${formatCandidateScore(candidate.score_rent)}, 교통 ${formatCandidateScore(candidate.score_transit)}, 시설 ${formatCandidateScore(candidate.score_amenity)}, 안전 ${formatCandidateScore(candidate.score_safety)}`;
  });
  return `담은 동네 후보들을 비교해줘.\n${lines.join('\n')}\n\n각 후보의 장단점, 내 선택에 중요한 질문, 추천 순서를 일반 사용자가 이해하기 쉽게 정리해줘.`;
}

function AiMapPanel() {
  const adongScoresQuery = useAdongScores(DEFAULT_WEIGHTS);

  return (
    <div className="h-full min-h-[420px]">
      <HeatMap
        adongs={adongScoresQuery.data ?? []}
        heatmapVisible={false}
        mode="score"
        regionLevel="adong"
      />
    </div>
  );
}

export default function AiChatPage() {
  const { user, isLoading: authLoading } = useAuth();
  const [searchParams] = useSearchParams();
  const compareCandidates = searchParams.get('context') === 'candidates';

  return (
    <main className="h-screen overflow-hidden bg-primary-soft text-text">
      <section className="mx-auto grid h-full w-full max-w-[1280px] box-border gap-5 px-5 py-16 sm:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(420px,500px)]">
        <div className="min-h-0 overflow-hidden rounded-sm border border-border bg-surface shadow-floating">
          <AiMapPanel />
        </div>
        <div className="grid min-h-0 content-center gap-4">
          <h1 className="m-0 text-[28px] font-semibold leading-tight tracking-normal sm:text-[32px]">
            {compareCandidates ? 'AI와 담은 동네 비교하기' : 'AI와 대화로 동네 찾아보기'}
          </h1>
        <AiChatDialog
          publicMode={AI_AGENT_PUBLIC_MODE}
          authLoading={authLoading}
          isAuthenticated={Boolean(user)}
          compareCandidates={compareCandidates}
        />
        </div>
      </section>
    </main>
  );
}

function AiChatDialog({
  publicMode,
  authLoading,
  isAuthenticated,
  compareCandidates,
}: {
  publicMode: boolean;
  authLoading: boolean;
  isAuthenticated: boolean;
  compareCandidates: boolean;
}) {
  const [keyStatus, setKeyStatus] = useState<AIAPIKeyStatusResponse | null>(null);
  const [keyStatusLoading, setKeyStatusLoading] = useState(false);
  const [keyStatusError, setKeyStatusError] = useState<string | null>(null);

  const refreshKeyStatus = useCallback(async () => {
    if (publicMode) return;
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
  }, [isAuthenticated, publicMode]);

  useEffect(() => {
    void refreshKeyStatus();
  }, [refreshKeyStatus]);

  const hasConfiguredKey = publicMode || (keyStatus?.keys.some((key) => key.configured) ?? false);
  const hasUnlockedKey =
    publicMode || (keyStatus?.keys.some((key) => key.configured && key.unlocked) ?? false);

  return (
      <section className="flex h-[calc(100vh-172px)] min-h-0 w-full flex-col overflow-hidden rounded-sm border border-border bg-surface text-text shadow-floating">

        {!publicMode && (authLoading || keyStatusLoading) ? (
          <GateMessage title="확인 중" message="AI 사용 가능 상태를 확인하고 있습니다." />
        ) : null}
        {!publicMode && !authLoading && !isAuthenticated ? (
          <GateMessage
            title="로그인이 필요합니다"
            message="AI 질의는 로그인 후 사용할 수 있습니다."
            action={<Link className="app-floating-button h-10 min-h-10 no-underline" to="/select?auth=login">로그인하기</Link>}
          />
        ) : null}
        {!publicMode && !authLoading && isAuthenticated && keyStatusError ? (
          <GateMessage title="상태 확인 실패" message={keyStatusError} action={<GateButton onClick={refreshKeyStatus}>다시 시도</GateButton>} />
        ) : null}
        {!publicMode && !authLoading && isAuthenticated && keyStatus && !hasConfiguredKey ? (
          <GateMessage
            title="API KEY가 필요합니다"
            message="마이페이지에서 AI API KEY를 먼저 등록해주세요."
            action={<Link className="app-floating-button h-10 min-h-10 no-underline" to="/select?auth=mypage">마이페이지로 이동</Link>}
          />
        ) : null}
        {!publicMode && !authLoading && isAuthenticated && keyStatus && hasConfiguredKey && !hasUnlockedKey ? (
          <UnlockGate onUnlocked={refreshKeyStatus} />
        ) : null}
        {publicMode || (!authLoading && isAuthenticated && keyStatus && hasUnlockedKey) ? (
          <ChatWorkspace canUseDemo={!publicMode && Boolean(keyStatus?.can_use_demo)} compareCandidates={compareCandidates} />
        ) : null}
      </section>
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
        <Link className="text-center text-[12px] font-semibold text-primary hover:text-primary-hover" to="/select?auth=mypage">
          API KEY 등록은 마이페이지에서 하기
        </Link>
      </div>
    </form>
  );
}

function ChatWorkspace({ canUseDemo, compareCandidates }: { canUseDemo: boolean; compareCandidates: boolean }) {
  const candidatePrompt = useMemo(() => (compareCandidates ? buildCandidateComparePrompt() : ''), [compareCandidates]);
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: 0,
      role: 'ai',
      text: compareCandidates
        ? '담은 동네 후보를 비교할 수 있게 질문을 준비했습니다.'
        : '안녕하세요. 원하는 조건을 입력하면 지역 데이터를 바탕으로 답변합니다.',
    },
  ]);
  const [input, setInput] = useState(candidatePrompt);
  const [isSending, setIsSending] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setConversationId(undefined);
    setMessages([
      {
        id: nextMessageId++,
        role: 'ai',
        text: compareCandidates
          ? candidatePrompt
            ? '담은 동네 후보를 비교할 수 있게 질문을 준비했습니다.'
            : '담은 동네가 없습니다. 후보를 담은 뒤 다시 물어볼 수 있습니다.'
          : '안녕하세요. 원하는 조건을 입력하면 지역 데이터를 바탕으로 답변합니다.',
      },
    ]);
    setInput(candidatePrompt);
  }, [candidatePrompt, compareCandidates]);

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
        text: compareCandidates ? '담은 동네 비교 대화를 새로 시작합니다.' : '새 대화를 시작합니다.',
      },
    ]);
    setInput(compareCandidates ? candidatePrompt : '');
  };

  return (
    <>
        <div className="flex items-center justify-between gap-3 border-b border-divider px-5 py-2">
        <span className="text-[12px] text-text-muted">
          {conversationId ? '대화 이어가는 중' : '새 대화'} · 새로고침하면 현재 대화가 초기화됩니다.
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
            placeholder={compareCandidates ? '예: 담은 후보 중 교통 좋은 곳부터 비교해줘' : '예: 월세 낮고 카페 많은 동네 추천해줘'}
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
              to={`/map?mode=plain&ai_lat=${point.lat}&ai_lng=${point.lng}&ai_label=${encodeURIComponent(point.label)}`}
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
