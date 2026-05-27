// Translate axios errors from the auth/users API into a single Korean string.
//
// Backend (step9a) already returns Korean copy via:
//   - { detail: "..." }
//   - { username: ["..."], password: ["..."] }
//   - { weights: ["..."] }
// We just flatten that into something the form can render directly.
import axios from 'axios';

import type { ApiErrorDetail } from '@/types/api';

/** Pull a presentable Korean error message from any error.
 *  - axios with `response.data.detail` → that string
 *  - axios with field validation errors → first field's first message
 *  - other → fallback
 */
export function getAuthErrorMessage(err: unknown, fallback: string): string {
  if (!axios.isAxiosError(err)) {
    if (err instanceof Error) return err.message || fallback;
    return fallback;
  }

  const status = err.response?.status;
  const data = err.response?.data as ApiErrorDetail | undefined;

  if (data) {
    if (typeof data.detail === 'string' && data.detail.length > 0) {
      return data.detail;
    }
    const fields: Array<keyof ApiErrorDetail> = [
      'username',
      'password',
      'slug',
      'weights',
      'w_rent',
      'w_amenity',
      'w_transit',
    ];
    for (const f of fields) {
      const v = data[f];
      if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'string') {
        return v[0];
      }
      if (typeof v === 'string' && v.length > 0) {
        return v;
      }
    }
  }

  if (status === 0 || status === undefined) {
    return '네트워크 오류가 발생했습니다. 백엔드 연결을 확인해주세요.';
  }
  return fallback;
}
