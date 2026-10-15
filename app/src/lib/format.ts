/** "방금 전", "5분 전", "3시간 전", "2일 전", 그 이상은 날짜 */
export function timeAgo(iso: string, now: Date = new Date()): string {
  const diff = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return '방금 전';
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}일 전`;
  const d = new Date(iso);
  return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

/** "오늘 19:00", "내일 7:30", "10월 15일(수) 19:00" */
export function whenLabel(iso: string, now: Date = new Date()): string {
  const d = new Date(iso);
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((startOf(d) - startOf(now)) / 86400000);
  const time = `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
  if (days === 0) return `오늘 ${time}`;
  if (days === 1) return `내일 ${time}`;
  if (days === 2) return `모레 ${time}`;
  return `${d.getMonth() + 1}월 ${d.getDate()}일(${WEEKDAYS[d.getDay()]}) ${time}`;
}

export const KIND_LABEL = { walk: '산책', share: '나눔' } as const;
export const GATHERING_STATUS_LABEL = { open: '모집 중', closed: '마감', cancelled: '취소됨' } as const;
export const LEVEL_LABEL = { none: '', neighbor: '이웃', regular: '단골 이웃' } as const;

export const SPECIES_LABEL = { all: '모두', dog: '강아지', cat: '고양이' } as const;

export const FAVOR_KIND_LABEL = { meal: '밥 주기', walk: '산책', hospital: '병원 동행', etc: '기타' } as const;
export const FAVOR_STATUS_LABEL = { open: '찾는 중', matched: '약속됨', done: '완료', cancelled: '취소됨' } as const;
export const SIZE_LABEL = { S: '소형', M: '중형', L: '대형', '': '' } as const;

/** 30 → "30분", 90 → "1시간 30분" */
export function minutesLabel(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return [h ? `${h}시간` : '', m ? `${m}분` : ''].filter(Boolean).join(' ');
}
