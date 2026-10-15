import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';

import { api } from '@/lib/api';

export type Unread = { notifications: number; messages: number };

/** 화면에 들어올 때마다 안 읽은 알림·쪽지 수를 가져온다 */
export function useUnread() {
  const [unread, setUnread] = useState<Unread>({ notifications: 0, messages: 0 });
  useFocusEffect(
    useCallback(() => {
      let alive = true;
      api<Unread>('/notifications/unread')
        .then((u) => alive && setUnread(u))
        .catch(() => {});
      return () => {
        alive = false;
      };
    }, []),
  );
  return unread;
}
