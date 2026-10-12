import { createContext, use, useCallback, useEffect, useMemo, useState, type PropsWithChildren } from 'react';

import { api, setSessionExpiredHandler, type Me } from '@/lib/api';
import { loadTokens, saveTokens, type Tokens } from '@/lib/token-storage';

type Session = {
  isLoading: boolean;
  isSignedIn: boolean;
  me: Me | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, nickname: string) => Promise<void>;
  signOut: () => Promise<void>;
  reloadMe: () => Promise<void>;
};

const SessionContext = createContext<Session | null>(null);

export function useSession() {
  const value = use(SessionContext);
  if (!value) throw new Error('useSession must be wrapped in a <SessionProvider />');
  return value;
}

export function SessionProvider({ children }: PropsWithChildren) {
  const [isLoading, setIsLoading] = useState(true);
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [me, setMe] = useState<Me | null>(null);

  const reloadMe = useCallback(async () => {
    setMe(await api<Me>('/me'));
  }, []);

  const start = useCallback(
    async (tokens: Tokens) => {
      await saveTokens(tokens);
      setIsSignedIn(true);
      await reloadMe();
    },
    [reloadMe],
  );

  const clear = useCallback(async () => {
    await saveTokens(null);
    setIsSignedIn(false);
    setMe(null);
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setIsSignedIn(false);
      setMe(null);
    });
    (async () => {
      const tokens = await loadTokens();
      if (tokens) {
        setIsSignedIn(true);
        try {
          await reloadMe();
        } catch {
          // 네트워크 오류 등: 로그인 상태는 유지하고 화면에서 다시 시도
        }
      }
      setIsLoading(false);
    })();
    return () => setSessionExpiredHandler(null);
  }, [reloadMe]);

  const value = useMemo<Session>(
    () => ({
      isLoading,
      isSignedIn,
      me,
      reloadMe,
      signIn: async (email, password) => {
        const tokens = await api<Tokens>('/auth/login', { method: 'POST', body: { email, password }, auth: false });
        await start(tokens);
      },
      signUp: async (email, password, nickname) => {
        const tokens = await api<Tokens>('/auth/signup', {
          method: 'POST',
          body: { email, password, nickname },
          auth: false,
        });
        await start(tokens);
      },
      signOut: async () => {
        const tokens = await loadTokens();
        if (tokens) {
          // 서버에서 refresh 토큰 폐기. 실패해도 기기에서는 로그아웃한다.
          await api('/auth/logout', { method: 'POST', body: { refresh: tokens.refresh } }).catch(() => {});
        }
        await clear();
      },
    }),
    [isLoading, isSignedIn, me, reloadMe, start, clear],
  );

  return <SessionContext value={value}>{children}</SessionContext>;
}
