import { router } from 'expo-router';

import type { Author } from './api';

/** 그 사람과의 쪽지 화면 */
export function openChat(user: Author) {
  router.push({ pathname: '/messages/[userId]', params: { userId: String(user.id), name: user.nickname } });
}
