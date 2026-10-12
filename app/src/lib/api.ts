import { API_URL } from './config';
import { loadTokens, saveTokens, type Tokens } from './token-storage';

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(extractMessage(body) ?? `요청에 실패했습니다 (${status})`);
  }
}

/** DRF 오류 응답에서 사람이 읽을 첫 메시지를 뽑는다. */
function extractMessage(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null;
  const record = body as Record<string, unknown>;
  if (typeof record.detail === 'string') return record.detail;
  for (const value of Object.values(record)) {
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
    if (typeof value === 'string') return value;
  }
  return null;
}

let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler;
}

let refreshing: Promise<Tokens | null> | null = null;

async function refreshTokens(refresh: string): Promise<Tokens | null> {
  const res = await fetch(`${API_URL}/api/v1/auth/token/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return null;
  const data = (await res.json()) as Partial<Tokens>;
  // 서버가 refresh 토큰을 회전시키므로 새 refresh도 함께 저장
  const tokens = { access: data.access!, refresh: data.refresh ?? refresh };
  await saveTokens(tokens);
  return tokens;
}

type RequestOptions = { method?: string; body?: unknown; auth?: boolean };

/**
 * 서버 호출. access 토큰이 만료(401)되면 refresh로 한 번 갱신 후 재시도한다.
 * 갱신도 실패하면 세션 만료 처리(로그아웃)한다.
 *
 * path: '/posts' 처럼 /api/v1 아래 경로, 또는 페이지네이션 next 같은 전체 URL.
 * body: 객체면 JSON, FormData면 multipart로 보낸다.
 */
export async function api<T = unknown>(path: string, { method = 'GET', body, auth = true }: RequestOptions = {}): Promise<T> {
  const url = /^https?:\/\//.test(path) ? path : `${API_URL}/api/v1${path}`;
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
  const send = (access?: string) =>
    fetch(url, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && !isForm ? { 'Content-Type': 'application/json' } : {}),
        ...(access ? { Authorization: `Bearer ${access}` } : {}),
      },
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    });

  let tokens = auth ? await loadTokens() : null;
  let res = await send(tokens?.access);

  if (res.status === 401 && auth && tokens?.refresh) {
    refreshing ??= refreshTokens(tokens.refresh).finally(() => {
      refreshing = null;
    });
    tokens = await refreshing;
    if (!tokens) {
      await saveTokens(null);
      onSessionExpired?.();
      throw new ApiError(401, { detail: '다시 로그인해 주세요.' });
    }
    res = await send(tokens.access);
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

// ---- 타입 (서버 OpenAPI 스펙과 맞춘다. 이후 openapi-typescript로 자동 생성 예정) ----

export type Me = {
  id: number;
  email: string | null;
  nickname: string;
  region_name: string;
  latitude: number | null;
  longitude: number | null;
  is_identity_verified: boolean;
  is_verified_member: boolean;
};

export type Pet = {
  id: number;
  user: number;
  name: string;
  species: 'dog' | 'cat';
  breed: string;
  sex: 'M' | 'F' | '';
  birthday: string | null;
  age: number | null;
  neutered: boolean | null;
  vaccinated: boolean | null;
  size: 'S' | 'M' | 'L' | '';
  weight_kg: string | null;
  traits: string[];
  verification_status: 'unverified' | 'pending' | 'approved' | 'rejected';
};

export type Page<T> = { next: string | null; previous: string | null; results: T[] };

export type Author = { id: number; nickname: string };
export type ImageInfo = { id: number; url: string; width: number; height: number };

export type Post = {
  id: number;
  author: Author;
  region_name: string;
  species: 'all' | 'dog' | 'cat';
  title: string;
  content: string;
  tags: string[];
  images: ImageInfo[];
  like_count: number;
  comment_count: number;
  is_liked: boolean;
  is_mine: boolean;
  is_hidden: boolean;
  created_at: string;
  updated_at: string;
};

export type Comment = {
  id: number;
  post: number;
  author: Author;
  content: string;
  is_mine: boolean;
  is_hidden: boolean;
  created_at: string;
};

export type ReportReason = 'money' | 'spam' | 'abuse' | 'danger' | 'other';

/** 기기 사진을 서버에 올리고 id를 받는다. (서버가 JPEG 변환·위치정보 제거) */
export async function uploadImage(asset: { uri: string; mimeType?: string | null; fileName?: string | null }) {
  const form = new FormData();
  // React Native의 FormData는 { uri, name, type } 객체로 파일을 보낸다.
  form.append('file', {
    uri: asset.uri,
    name: asset.fileName ?? 'photo.jpg',
    type: asset.mimeType ?? 'image/jpeg',
  } as unknown as Blob);
  return api<ImageInfo>('/uploads/images', { method: 'POST', body: form });
}
