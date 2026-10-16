import { File } from 'expo-file-system';
import { Platform } from 'react-native';

import { API_URL } from './config';
import { loadTokens, saveTokens, type Tokens } from './token-storage';

const TIMEOUT_MS = 15_000;
const UPLOAD_TIMEOUT_MS = 60_000;

/** 응답이 없으면 무한 대기하지 않고 안내 메시지로 실패시킨다. */
async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs = TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch {
    throw new ApiError(0, { detail: '서버에 연결할 수 없어요. 네트워크를 확인하고 다시 시도해 주세요.' });
  } finally {
    clearTimeout(timer);
  }
}

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
  const res = await fetchWithTimeout(`${API_URL}/api/v1/auth/token/refresh`, {
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
    fetchWithTimeout(url, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && !isForm ? { 'Content-Type': 'application/json' } : {}),
        ...(access ? { Authorization: `Bearer ${access}` } : {}),
      },
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    }, isForm ? UPLOAD_TIMEOUT_MS : TIMEOUT_MS);

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

export type PetBrief = Pick<Pet, 'id' | 'name' | 'species' | 'breed' | 'size' | 'weight_kg'>;

export type Participation = {
  id: number;
  user: Author;
  pet: PetBrief | null;
  message: string;
  status: 'pending' | 'accepted' | 'rejected' | 'cancelled';
  created_at: string;
  decided_at: string | null;
};

export type Gathering = {
  id: number;
  host: Author;
  kind: 'walk' | 'share';
  species: 'all' | 'dog' | 'cat';
  region_name: string;
  title: string;
  content: string;
  place_name: string;
  starts_at: string;
  capacity: number;
  status: 'open' | 'closed' | 'cancelled';
  accepted_count: number;
  participants: Participation[];
  my_participation: Participation | null;
  is_host: boolean;
  is_hidden: boolean;
  created_at: string;
};

export type Neighbor = {
  id: number;
  nickname: string;
  meet_count: number;
  last_met_on: string;
  favors_done: number;
  level: 'none' | 'neighbor' | 'regular';
};

export type CareSheetInput = {
  meal: { times_per_day: number | null; amount: string; food: string };
  meds: { name: string; dose: string; time: string }[];
  condition: string;
  walk: { minutes: number | null; per_week: number | null };
  notes: string;
  caution: string;
};

export type CareSheet = CareSheetInput & {
  basic: {
    name: string;
    species: string;
    breed: string;
    sex: string;
    age: number | null;
    size: string;
    weight_kg: number | null;
    neutered: boolean | null;
    vaccinated: boolean | null;
    traits: string[];
  };
};

export type CareSheetDraft = CareSheet & { source: { days: number; from_journal: string[] } };

export type FavorApplication = {
  id: number;
  user: Author;
  message: string;
  status: 'pending' | 'accepted' | 'rejected' | 'cancelled';
  agreed_at: string;
  created_at: string;
  decided_at: string | null;
};

export type Favor = {
  id: number;
  requester: Author;
  pet: PetBrief;
  kind: 'meal' | 'walk' | 'hospital' | 'etc';
  visit_home: boolean;
  region_name: string;
  title: string;
  content: string;
  place_name: string;
  starts_at: string;
  duration_minutes: number;
  care_summary: {
    species: string | null;
    breed: string;
    size: string;
    age: number | null;
    traits: string[];
    walk: { minutes: number | null; per_week: number | null };
  };
  /** 보호자와 맡은 이웃에게만 */
  care_sheet: CareSheet | null;
  status: 'open' | 'matched' | 'done' | 'cancelled';
  helper: Author | null;
  matched_at: string | null;
  /** 맡은 이웃이 '다 했어요'를 누른 시각 */
  helper_reported_at: string | null;
  /** 보호자가 지금 '확인했어요'를 누를 수 있는지 */
  can_confirm: boolean;
  completed_at: string | null;
  is_requester: boolean;
  my_application: FavorApplication | null;
  can_help: boolean;
  cannot_help_reason: string;
  pending_count: number | null;
  thanks: { message: string; created_at: string } | null;
  is_hidden: boolean;
  created_at: string;
};

export type PlaceCategory =
  | 'cafe' | 'restaurant' | 'stay' | 'attraction' | 'park' | 'hospital' | 'pharmacy' | 'grooming' | 'hotel' | 'etc';
export type PlaceSpace = 'indoor' | 'outdoor' | 'separate';

export type PlaceConditions = {
  large_ok: boolean | null;
  space: PlaceSpace | '';
  floor_ok: boolean | null;
  extra_fee: boolean | null;
  review_count: number;
  large_reviews: number;
  max_weight_admitted: number | null;
  last_checked: string | null;
  differs_from_policy: boolean;
};

export type Place = {
  id: number;
  name: string;
  category: PlaceCategory;
  address: string;
  lat: number;
  lng: number;
  phone: string;
  region_name: string;
  status: 'pending' | 'approved' | 'closed';
  source: string;
  naver_booking_url: string;
  naver_place_url: string;
  is_24h: boolean;
  hours: string;
  sizes_allowed: ('S' | 'M' | 'L')[];
  max_weight_kg: number | null;
  space: PlaceSpace | '';
  floor_ok: boolean | null;
  max_pets: number | null;
  restricted_breeds: string;
  fee_per_pet: number | null;
  cats_ok: boolean | null;
  amenities: string[];
  policy_checked_at: string | null;
  distance_m: number | null;
  conditions: PlaceConditions;
  /** ?pet= 으로 고른 반려동물 기준 */
  fit: 'yes' | 'no' | 'unknown';
  kakao: { view: string; directions: string };
  is_mine: boolean;
};

export type PlaceReview = {
  id: number;
  user: Author;
  pet_species: 'dog' | 'cat';
  pet_size: 'S' | 'M' | 'L' | '';
  pet_weight_kg: string | null;
  visited_on: string;
  admitted: boolean;
  space: PlaceSpace | '';
  floor_ok: boolean | null;
  extra_fee: boolean | null;
  comment: string;
  verified_visit: boolean;
  images: ImageInfo[];
  is_mine: boolean;
  is_hidden: boolean;
  created_at: string;
};

export type JournalKind = 'daily' | 'walk' | 'health';

export type JournalEntry = {
  id: number;
  pet_id: number;
  kind: JournalKind;
  date: string;
  title: string;
  content: string;
  share_in_care_sheet: boolean;
  started_at: string | null;
  ended_at: string | null;
  duration_sec: number | null;
  distance_m: number | null;
  /** [[lat, lng], ...] 본인만 */
  route: [number, number][];
  meals_per_day: number | null;
  meal_amount: string;
  food: string;
  vitality: number | null;
  /** null = 기록 안 함, [] = 먹는 약 없음 */
  meds: { name: string; dose: string; time: string }[] | null;
  weight_kg: string | null;
  images: ImageInfo[];
  created_at: string;
  updated_at: string;
};

export type CalendarDay = { date: string; kinds: JournalKind[]; walk_minutes: number; count: number };

export type AppNotification = {
  id: number;
  kind: string;
  title: string;
  body: string;
  path: string;
  read_at: string | null;
  created_at: string;
};

export type Message = {
  id: number;
  sender: Author;
  recipient: Author;
  content: string;
  read_at: string | null;
  is_mine: boolean;
  created_at: string;
};

export type Thread = { user: Author; last: Message; unread: number };

export type ReportReason = 'money' | 'spam' | 'abuse' | 'danger' | 'other';

/** 기기 사진을 서버에 올리고 id를 받는다. (서버가 JPEG 변환·위치정보 제거) */
export async function uploadImage(asset: { uri: string; mimeType?: string | null; fileName?: string | null }) {
  const form = new FormData();
  const name = asset.fileName ?? 'photo.jpg';
  if (Platform.OS === 'web') {
    form.append('file', await (await fetch(asset.uri)).blob(), name);
  } else {
    // Expo SDK 57의 fetch는 RN식 { uri, name, type } 첨부를 지원하지 않는다.
    // expo-file-system의 File(Blob 구현체)로 넣어야 한다.
    form.append('file', new File(asset.uri) as unknown as Blob, name);
  }
  return api<ImageInfo>('/uploads/images', { method: 'POST', body: form });
}
