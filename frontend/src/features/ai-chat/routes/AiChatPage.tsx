import { Navigate, useLocation } from 'react-router-dom';

export default function AiChatPage() {
  const location = useLocation();
  const search = new URLSearchParams(location.search);
  const context = search.get('context');
  const next = new URLSearchParams({ ai: '1' });
  if (context) next.set('context', context);

  return <Navigate to={`/recommend/conditions?${next.toString()}`} replace />;
}
