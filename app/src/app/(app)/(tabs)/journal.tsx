import { router, useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Chips } from '@/components/chips';
import { ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, type CalendarDay, type JournalEntry, type JournalKind, type Page, type Pet } from '@/lib/api';
import { clock, distanceLabel, isoDate, JOURNAL_KIND_LABEL, VITALITY_LABEL } from '@/lib/format';

const WEEK = ['일', '월', '화', '수', '목', '금', '토'];
const KIND_ICON: Record<JournalKind, string> = { walk: '🐾', health: '💊', daily: '📝' };

function monthKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

/** 달력 칸: 앞쪽 빈칸(null) + 1일~말일 */
function monthCells(first: Date): (Date | null)[] {
  const days = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
  return [
    ...Array.from({ length: first.getDay() }, () => null),
    ...Array.from({ length: days }, (_, i) => new Date(first.getFullYear(), first.getMonth(), i + 1)),
  ];
}

export function entrySummary(e: JournalEntry): string {
  if (e.kind === 'walk') {
    return [e.duration_sec ? clock(e.duration_sec) : null, e.distance_m ? distanceLabel(e.distance_m) : null].filter(Boolean).join(' · ');
  }
  if (e.kind === 'health') {
    return [
      e.vitality ? `활력 ${e.vitality} ${VITALITY_LABEL[e.vitality]}` : null,
      e.meals_per_day != null ? `하루 ${e.meals_per_day}끼` : null,
      e.meds ? (e.meds.length ? `약 ${e.meds.map((m) => m.name).join(', ')}` : '약 없음') : null,
      e.weight_kg ? `${Number(e.weight_kg)}kg` : null,
    ]
      .filter(Boolean)
      .join(' · ');
  }
  return e.title || e.content.split('\n')[0];
}

export default function Journal() {
  const theme = useTheme();
  const today = useMemo(() => new Date(), []);
  const [pets, setPets] = useState<Pet[] | null>(null);
  const [petId, setPetId] = useState('');
  const [month, setMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [selected, setSelected] = useState(() => isoDate(today));
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const req = useRef(0);

  useFocusEffect(
    useCallback(() => {
      api<Page<Pet>>('/pets')
        .then((page) => {
          setPets(page.results);
          setPetId((cur) => cur || (page.results[0] ? String(page.results[0].id) : ''));
        })
        .catch((e) => setError(e instanceof Error ? e.message : '반려동물을 불러오지 못했어요.'));
    }, []),
  );

  const load = useCallback(async () => {
    if (!petId) return;
    const id = ++req.current;
    try {
      const [cal, list] = await Promise.all([
        api<CalendarDay[]>(`/journal/calendar?month=${monthKey(month)}&pet=${petId}`),
        api<Page<JournalEntry>>(`/journal?pet=${petId}&date=${selected}`),
      ]);
      if (id !== req.current) return;
      setDays(cal);
      setEntries(list.results);
      setError(null);
    } catch (e) {
      if (id === req.current) setError(e instanceof Error ? e.message : '일기를 불러오지 못했어요.');
    }
  }, [petId, month, selected]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const byDate = useMemo(() => Object.fromEntries(days.map((d) => [d.date, d])), [days]);
  const monthWalks = days.reduce((n, d) => n + (d.kinds.includes('walk') ? 1 : 0), 0);
  const monthMinutes = days.reduce((n, d) => n + d.walk_minutes, 0);
  const todayKey = isoDate(today);
  const isThisMonth = monthKey(month) === monthKey(today);
  const pet = pets?.find((p) => String(p.id) === petId);

  const go = (kind: 'walk' | 'health' | 'daily') => {
    if (!petId) return;
    if (kind === 'walk') router.push({ pathname: '/journal/walk', params: { pet: petId } });
    else router.push({ pathname: '/journal/new', params: { pet: petId, kind, date: selected } });
  };

  if (pets && pets.length === 0) {
    return (
      <ThemedView style={[styles.flex, styles.pad]}>
        <SafeAreaView edges={['top']}>
          <ThemedText type="subtitle">일기</ThemedText>
          <ThemedText themeColor="textSecondary" style={styles.top}>
            마이 탭에서 반려동물을 등록하면 산책·건강 일기를 쓸 수 있어요.
          </ThemedText>
        </SafeAreaView>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.flex}>
      <SafeAreaView style={styles.flex} edges={['top']}>
        <ScrollView contentContainerStyle={styles.container}>
          <ThemedText type="subtitle" style={styles.title}>
            일기
          </ThemedText>
          {pets && pets.length > 1 && (
            <Chips value={petId} onChange={setPetId} options={pets.map((p) => ({ value: String(p.id), label: p.name }))} />
          )}

          {/* 기록하기 */}
          <View style={styles.actions}>
            {(
              [
                ['walk', '🐾', '산책 시작'],
                ['health', '💊', '건강 기록'],
                ['daily', '📝', '일기 쓰기'],
              ] as const
            ).map(([kind, icon, label]) => (
              <Pressable
                key={kind}
                accessibilityRole="button"
                onPress={() => go(kind)}
                style={({ pressed }) => [
                  styles.action,
                  { backgroundColor: kind === 'walk' ? theme.primary : theme.backgroundElement, opacity: pressed ? 0.8 : 1 },
                ]}>
                <ThemedText style={styles.actionIcon}>{icon}</ThemedText>
                <ThemedText type="smallBold" style={kind === 'walk' ? { color: theme.onPrimary } : undefined}>
                  {label}
                </ThemedText>
              </Pressable>
            ))}
          </View>

          {/* 달력 */}
          <View style={styles.monthRow}>
            <ThemedText
              type="linkPrimary"
              accessibilityLabel="이전 달"
              onPress={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
              style={styles.arrow}>
              ‹
            </ThemedText>
            <ThemedText type="smallBold">
              {month.getFullYear()}년 {month.getMonth() + 1}월
            </ThemedText>
            <ThemedText
              type="linkPrimary"
              accessibilityLabel="다음 달"
              onPress={() => !isThisMonth && setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
              style={[styles.arrow, isThisMonth && { opacity: 0.3 }]}>
              ›
            </ThemedText>
          </View>
          <ThemedText type="small" themeColor="textSecondary" style={styles.center}>
            {monthWalks ? `${pet?.name ?? ''} 이번 달 산책 ${monthWalks}일 · ${monthMinutes}분` : '이번 달 산책 기록이 아직 없어요'}
          </ThemedText>
          <View style={styles.grid}>
            {WEEK.map((w) => (
              <ThemedText key={w} type="small" themeColor="textSecondary" style={styles.cellHead}>
                {w}
              </ThemedText>
            ))}
            {monthCells(month).map((d, i) => {
              if (!d) return <View key={`e${i}`} style={styles.cell} />;
              const key = isoDate(d);
              const info = byDate[key];
              const isSel = key === selected;
              const future = key > todayKey;
              return (
                <Pressable
                  key={key}
                  disabled={future}
                  onPress={() => setSelected(key)}
                  accessibilityLabel={`${d.getDate()}일${info ? `, 기록 ${info.count}개` : ''}`}
                  style={[styles.cell, isSel && { backgroundColor: theme.primary, borderRadius: 10 }]}>
                  <ThemedText
                    type="small"
                    style={[
                      { color: isSel ? theme.onPrimary : future ? theme.textSecondary : theme.text },
                      key === todayKey && !isSel && { fontWeight: 700, color: theme.primary },
                    ]}>
                    {d.getDate()}
                  </ThemedText>
                  <ThemedText style={styles.dots}>{info ? info.kinds.map((k) => KIND_ICON[k]).join('') : ' '}</ThemedText>
                </Pressable>
              );
            })}
          </View>

          {/* 선택한 날 */}
          <View style={styles.section}>
            <ThemedText type="smallBold">
              {selected === todayKey ? '오늘' : `${Number(selected.slice(5, 7))}월 ${Number(selected.slice(8))}일`}
            </ThemedText>
            <ErrorText message={error} />
            {entries.length === 0 && (
              <ThemedText type="small" themeColor="textSecondary">
                기록이 없어요. 산책·건강을 기록해 두면 이웃에게 부탁할 때 돌봄 시트가 자동으로 채워져요.
              </ThemedText>
            )}
            {entries.map((e) => (
              <Pressable
                key={e.id}
                accessibilityRole="button"
                onPress={() => router.push({ pathname: '/journal/[id]', params: { id: String(e.id) } })}
                style={({ pressed }) => [styles.entry, { borderColor: theme.border, opacity: pressed ? 0.7 : 1 }]}>
                <ThemedText>{KIND_ICON[e.kind]}</ThemedText>
                <View style={styles.flex}>
                  <ThemedText type="smallBold">
                    {JOURNAL_KIND_LABEL[e.kind]}
                    {e.share_in_care_sheet ? '  · 돌봄 시트에 넣음' : ''}
                  </ThemedText>
                  <ThemedText type="small" themeColor="textSecondary" numberOfLines={1}>
                    {entrySummary(e)}
                  </ThemedText>
                </View>
              </Pressable>
            ))}
          </View>
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  pad: { padding: Spacing.four },
  top: { marginTop: Spacing.three },
  container: { padding: Spacing.four, gap: Spacing.three, paddingBottom: Spacing.six },
  title: { fontSize: 24, lineHeight: 32 },
  actions: { flexDirection: 'row', gap: Spacing.two },
  action: { flex: 1, borderRadius: 14, paddingVertical: Spacing.three, alignItems: 'center', gap: 2 },
  actionIcon: { fontSize: 22, lineHeight: 28 },
  monthRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.four, marginTop: Spacing.two },
  arrow: { fontSize: 26, lineHeight: 30, paddingHorizontal: Spacing.three },
  center: { textAlign: 'center' },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  cellHead: { width: `${100 / 7}%`, textAlign: 'center', paddingVertical: 4 },
  cell: { width: `${100 / 7}%`, alignItems: 'center', paddingVertical: 4, minHeight: 48 },
  dots: { fontSize: 9, lineHeight: 14 },
  section: { gap: Spacing.two, marginTop: Spacing.two },
  entry: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three, paddingVertical: Spacing.three, borderBottomWidth: StyleSheet.hairlineWidth },
});
