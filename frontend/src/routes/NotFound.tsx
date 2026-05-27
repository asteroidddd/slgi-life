// 404 — empty state. DESIGN_SYSTEM.md `empty-state`: center text only,
// 큰 헤드라인 + 한 줄 설명 + 1개 secondary action. design-audit F-17.
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <main
      id="main"
      className="flex flex-col items-center justify-center text-center min-h-screen gap-4 p-6 text-text-muted"
    >
      <h1 className="m-0 text-section-heading leading-[1.15] font-normal text-text tracking-[-0.36px]">
        페이지를 찾을 수 없습니다
      </h1>
      <p className="m-0 max-w-[40ch] break-keep">
        주소가 바뀌었거나, 더 이상 사용하지 않는 페이지일 수 있어요. 메인 지도에서 다시
        시작해 주세요.
      </p>
      <Link
        to="/"
        className="text-link underline underline-offset-2"
      >
        ← 메인 지도로 돌아가기
      </Link>
    </main>
  );
}
