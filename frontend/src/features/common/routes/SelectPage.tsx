import { Link } from 'react-router-dom';

const actions = [
  {
    title: '조건으로 추천받기',
    description: '예산, 시설, 교통 조건을 고르면 맞는 동네 후보를 보여드립니다.',
    to: '/recommend/conditions',
  },
  {
    title: '지도에서 직접 찾기',
    description: '지도를 직접 보면서 시설, 의료, 점수 정보를 확인하고 마음에 드는 동네를 고릅니다.',
    to: '/map',
  },
];

export default function SelectPage() {
  return (
    <main className="min-h-screen bg-primary-soft text-text">
      <section className="mx-auto flex min-h-screen w-full max-w-[1120px] flex-col justify-center px-5 py-24 sm:px-8">
        <div className="mb-10 flex items-center gap-4">
          <img src="/logo.svg" alt="자취맵" className="h-14 w-14 rounded-sm bg-surface object-contain p-2 shadow-floating" />
          <div>
            <p className="m-0 text-caption font-semibold text-primary">자취맵</p>
            <h1 className="m-0 mt-1 text-[34px] font-semibold leading-tight tracking-normal sm:text-section-heading">
              어떤 방식으로 동네를 찾을까요?
            </h1>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {actions.map((action, index) => (
            <Link
              key={action.title}
              to={action.to}
              className="group min-h-[240px] rounded-sm border border-border bg-surface p-7 text-text no-underline shadow-floating transition hover:-translate-y-0.5 hover:border-primary hover:shadow-xl focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-focus-ring"
            >
              <span className="mb-8 inline-flex h-10 w-10 items-center justify-center rounded-sm bg-primary-soft text-[15px] font-semibold text-primary">
                {index + 1}
              </span>
              <h2 className="m-0 text-feature-heading font-semibold leading-snug">{action.title}</h2>
              <p className="m-0 mt-3 text-[14px] leading-6 text-text-muted">{action.description}</p>
              <span className="mt-8 inline-flex text-[13px] font-semibold text-primary group-hover:text-primary-hover">
                시작하기
              </span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
