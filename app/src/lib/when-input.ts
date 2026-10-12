const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

/** 오늘부터 n일 (날짜 칩용) */
export function nextDays(n = 7) {
  const today = new Date();
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + i);
    const label = i === 0 ? '오늘' : i === 1 ? '내일' : `${d.getMonth() + 1}/${d.getDate()}(${WEEKDAYS[d.getDay()]})`;
    return { value: String(i), label, date: d };
  });
}

/** "19:00", "7:30", "1930" → [시, 분] */
export function parseTime(raw: string): [number, number] | null {
  const m = raw.trim().match(/^(\d{1,2}):?(\d{2})$/);
  if (!m) return null;
  const h = Number(m[1]);
  const min = Number(m[2]);
  return h < 24 && min < 60 ? [h, min] : null;
}

export function combine(date: Date, hm: [number, number]): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), hm[0], hm[1]);
}
