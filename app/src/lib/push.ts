import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import { api } from './api';

let currentToken: string | null = null;

// 앱이 켜져 있을 때도 알림을 배너로 보여준다
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

export type PushStatus = { ok: true } | { ok: false; reason: string };

/**
 * 푸시 권한을 받고 Expo 푸시 토큰을 서버에 등록한다.
 * EAS 프로젝트 id(app.json의 extra.eas.projectId)가 있어야 토큰을 받을 수 있다.
 */
export async function registerForPush(): Promise<PushStatus> {
  if (Platform.OS === 'web') return { ok: false, reason: '웹에서는 푸시를 받을 수 없어요.' };
  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  if (!projectId) return { ok: false, reason: '푸시 설정(EAS 프로젝트 연결)이 아직 안 됐어요.' };

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: '기본',
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }
  let { status } = await Notifications.getPermissionsAsync();
  if (status !== 'granted') ({ status } = await Notifications.requestPermissionsAsync());
  if (status !== 'granted') return { ok: false, reason: '알림 권한이 꺼져 있어요. 설정에서 켜 주세요.' };

  try {
    const { data } = await Notifications.getExpoPushTokenAsync({ projectId });
    await api('/devices', { method: 'POST', body: { token: data, platform: Platform.OS } });
    currentToken = data;
    return { ok: true };
  } catch (e) {
    return { ok: false, reason: e instanceof Error ? e.message : '푸시 토큰을 받지 못했어요.' };
  }
}

/** 로그아웃할 때 이 기기로 푸시가 가지 않게 한다 */
export async function unregisterPush() {
  if (!currentToken) return;
  await api('/devices', { method: 'DELETE', body: { token: currentToken } }).catch(() => {});
  currentToken = null;
}

/** 알림을 눌렀을 때 열 화면 */
export function pathOfResponse(r: Notifications.NotificationResponse): string | null {
  const path = r.notification.request.content.data?.path;
  return typeof path === 'string' && path.startsWith('/') ? path : null;
}
