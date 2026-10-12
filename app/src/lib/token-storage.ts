import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/** 토큰은 기기 보안 저장소(Keychain/Keystore)에 둔다. 웹은 개발 확인용. */
export type Tokens = { access: string; refresh: string };

const KEY = 'meongnyang.tokens';

export async function loadTokens(): Promise<Tokens | null> {
  try {
    const raw =
      Platform.OS === 'web' ? globalThis.localStorage?.getItem(KEY) ?? null : await SecureStore.getItemAsync(KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

export async function saveTokens(tokens: Tokens | null): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      if (tokens) globalThis.localStorage?.setItem(KEY, JSON.stringify(tokens));
      else globalThis.localStorage?.removeItem(KEY);
      return;
    }
    if (tokens) await SecureStore.setItemAsync(KEY, JSON.stringify(tokens));
    else await SecureStore.deleteItemAsync(KEY);
  } catch {
    // 저장 실패 시에도 앱은 메모리 상태로 계속 동작
  }
}
