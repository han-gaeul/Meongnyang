import { useKeepAwake } from 'expo-keep-awake';
import * as Location from 'expo-location';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, StyleSheet, TextInput, View } from 'react-native';

import { Agree, Button, ErrorText } from '@/components/form';
import { KakaoMap, kakaoMapAvailable } from '@/components/kakao-map';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, type JournalEntry } from '@/lib/api';
import { clock, distanceLabel, isoDate } from '@/lib/format';
import { distanceM, pathLength } from '@/lib/geo';

type Phase = 'ready' | 'recording' | 'done';

// GPS 정확도가 이보다 나쁘면(실내·지하) 경로에 넣지 않는다
const MAX_ACCURACY_M = 35;

function KeepAwake() {
  useKeepAwake('walk');
  return null;
}

/** 산책 기록. 화면을 켜 둔 동안 GPS로 경로·시간·거리를 잰다. */
export default function WalkRecorder() {
  const { pet } = useLocalSearchParams<{ pet: string }>();
  const theme = useTheme();
  const [phase, setPhase] = useState<Phase>('ready');
  const [path, setPath] = useState<[number, number][]>([]);
  const [startedAt, setStartedAt] = useState<Date | null>(null);
  const [endedAt, setEndedAt] = useState<Date | null>(null);
  const [now, setNow] = useState(0);
  const [memo, setMemo] = useState('');
  const [share, setShare] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sub = useRef<Location.LocationSubscription | null>(null);

  useEffect(() => {
    if (phase !== 'recording') return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [phase]);

  useEffect(() => () => sub.current?.remove(), []);

  const start = async () => {
    setError(null);
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      setError('위치 권한이 필요해요. 설정에서 위치 접근을 허용해 주세요.');
      return;
    }
    const begin = new Date();
    setStartedAt(begin);
    setNow(begin.getTime());
    setPhase('recording');
    sub.current = await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.BestForNavigation, distanceInterval: 5, timeInterval: 3000 },
      (loc) => {
        if (loc.coords.accuracy != null && loc.coords.accuracy > MAX_ACCURACY_M) return;
        const pt: [number, number] = [loc.coords.latitude, loc.coords.longitude];
        setPath((prev) => {
          // 제자리 떨림은 버린다
          if (prev.length && distanceM(prev[prev.length - 1], pt) < 3) return prev;
          return [...prev, pt];
        });
      },
    );
  };

  const stop = () => {
    sub.current?.remove();
    sub.current = null;
    setEndedAt(new Date());
    setPhase('done');
  };

  const save = async () => {
    if (!startedAt || !endedAt) return;
    setSaving(true);
    setError(null);
    try {
      const e = await api<JournalEntry>('/journal', {
        method: 'POST',
        body: {
          pet_id: Number(pet),
          kind: 'walk',
          date: isoDate(startedAt),
          started_at: startedAt.toISOString(),
          ended_at: endedAt.toISOString(),
          route: path,
          content: memo.trim(),
          share_in_care_sheet: share && !!memo.trim(),
        },
      });
      router.replace({ pathname: '/journal/[id]', params: { id: String(e.id) } });
    } catch (err) {
      setError(err instanceof Error ? err.message : '저장하지 못했어요.');
    } finally {
      setSaving(false);
    }
  };

  const distance = useMemo(() => pathLength(path), [path]);
  const elapsed = startedAt ? ((phase === 'done' && endedAt ? endedAt.getTime() : now) - startedAt.getTime()) / 1000 : 0;
  const last = path[path.length - 1];

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen options={{ title: '산책', gestureEnabled: phase !== 'recording' }} />
      {phase === 'recording' && <KeepAwake />}

      <View style={styles.map}>
        {kakaoMapAvailable && last ? (
          <KakaoMap
            center={{ lat: last[0], lng: last[1] }}
            markers={[]}
            selectedId={null}
            onSelect={() => {}}
            path={path}
            fitPath={phase === 'done'}
          />
        ) : (
          <ThemedView type="backgroundElement" style={[styles.flex, styles.mapEmpty]}>
            <ThemedText style={styles.paw}>🐾</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              {phase === 'ready' ? '시작하면 경로를 기록해요' : path.length ? `${path.length}개 지점 기록 중` : 'GPS 신호를 찾는 중…'}
            </ThemedText>
          </ThemedView>
        )}
      </View>

      <View style={styles.body}>
        <View style={styles.stats}>
          <View style={styles.stat}>
            <ThemedText type="small" themeColor="textSecondary">
              시간
            </ThemedText>
            <ThemedText style={styles.big}>{clock(elapsed)}</ThemedText>
          </View>
          <View style={styles.stat}>
            <ThemedText type="small" themeColor="textSecondary">
              거리
            </ThemedText>
            <ThemedText style={styles.big}>{distanceLabel(Math.round(distance)) || '0m'}</ThemedText>
          </View>
        </View>

        <ErrorText message={error} />

        {phase === 'ready' && (
          <>
            <Button title="산책 시작" onPress={start} />
            <ThemedText type="small" themeColor="textSecondary">
              기록하는 동안 이 화면을 켜 두세요. 지금은 앱을 닫거나 다른 앱으로 가면 기록이 멈춰요. 경로는 나만 볼 수 있어요.
            </ThemedText>
          </>
        )}

        {phase === 'recording' && (
          <Button
            title="산책 끝"
            onPress={() =>
              Alert.alert('산책 끝', '기록을 마칠까요?', [
                { text: '계속 걷기', style: 'cancel' },
                { text: '끝내기', onPress: stop },
              ])
            }
          />
        )}

        {phase === 'done' && (
          <>
            <TextInput
              value={memo}
              onChangeText={setMemo}
              maxLength={500}
              multiline
              placeholder="한 줄 메모 (선택) 예: 비둘기 보고 흥분함"
              placeholderTextColor={theme.textSecondary}
              style={[styles.input, { color: theme.text, borderColor: theme.border }]}
            />
            {!!memo.trim() && <Agree checked={share} onChange={setShare} label="이 메모를 부탁할 때 돌봄 시트에 넣기" />}
            <Button title="저장" onPress={save} loading={saving} disabled={elapsed < 60} />
            {elapsed < 60 && (
              <ThemedText type="small" themeColor="textSecondary">
                1분 이상 걸은 산책만 저장할 수 있어요.
              </ThemedText>
            )}
            <Button title="저장하지 않기" variant="secondary" onPress={() => router.back()} />
          </>
        )}
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  map: { height: 280 },
  mapEmpty: { alignItems: 'center', justifyContent: 'center', gap: Spacing.two },
  paw: { fontSize: 40, lineHeight: 48 },
  body: { padding: Spacing.four, gap: Spacing.three },
  stats: { flexDirection: 'row', gap: Spacing.three },
  stat: { flex: 1, alignItems: 'center', gap: 2 },
  big: { fontSize: 32, lineHeight: 40, fontWeight: 700, fontVariant: ['tabular-nums'] },
  input: { borderWidth: 1, borderRadius: 10, padding: Spacing.three, minHeight: 64, fontSize: 16 },
});
