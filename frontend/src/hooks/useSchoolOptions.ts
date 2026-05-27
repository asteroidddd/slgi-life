import { useQuery } from '@tanstack/react-query';

import { getSchoolOptions } from '@/lib/api';

export function useSchoolOptions() {
  return useQuery({
    queryKey: ['schools', 'options'] as const,
    queryFn: getSchoolOptions,
    staleTime: 3_600_000,
  });
}
