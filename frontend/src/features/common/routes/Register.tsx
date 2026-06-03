import { Navigate } from 'react-router-dom';

import { useAuth } from '@/features/common/contexts/AuthContext';

export default function Register() {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return <main className="min-h-screen bg-primary-soft p-8 text-center text-text-muted">불러오는 중...</main>;
  }
  return <Navigate to={user ? '/select?auth=mypage' : '/select?auth=login'} replace />;
}
