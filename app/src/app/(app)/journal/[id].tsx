import { Image } from 'expo-image';
import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, ScrollView, StyleSheet, View } from 'react-native';

import { ErrorText } from '@/components/form';
import { KakaoMap, kakaoMapAvailable } from '@/components/kakao-map';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { api, type JournalEntry } from '@/lib/api';
import { clock, distanceLabel, JOURNAL_KIND_LABEL, VITALITY_LABEL } from '@/lib/format';

function Row({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <View style={styles.row}>
      <ThemedText type="small" themeColor="textSecondary" style={styles.label}>
        {label}
      </ThemedText>
      <ThemedText type="small" style={styles.flex}>
        {value}
      </ThemedText>
    </View>
  );
}

const hm = (iso: string | null) => (iso ? new Date(iso).toTimeString().slice(0, 5) : '');

export default function JournalDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [e, setE] = useState<JournalEntry | null>(null);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      api<JournalEntry>(`/journal/${id}`)
        .then(setE)
        .catch((err) => setError(err instanceof Error ? err.message : '불러오지 못했어요.'));
    }, [id]),
  );

  const remove = () =>
    Alert.alert('기록 삭제', '이 기록을 지울까요?', [
      { text: '아니요', style: 'cancel' },
      {
        text: '지우기',
        style: 'destructive',
        onPress: async () => {
          try {
            await api(`/journal/${id}`, { method: 'DELETE' });
            router.back();
          } catch (err) {
            setError(err instanceof Error ? err.message : '지우지 못했어요.');
          }
        },
      },
    ]);

  const route = e?.route ?? [];
  const mid = route[Math.floor(route.length / 2)];

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen
        options={{
          title: e ? `${e.date.replace(/-/g, '.')} ${JOURNAL_KIND_LABEL[e.kind]}` : '',
          headerRight: () =>
            e ? (
              <ThemedText type="linkPrimary" onPress={remove} accessibilityRole="button" style={styles.headerAction}>
                삭제
              </ThemedText>
            ) : null,
        }}
      />
      <ScrollView contentContainerStyle={styles.container}>
        <ErrorText message={error} />
        {e?.kind === 'walk' && (
          <>
            {kakaoMapAvailable && route.length > 1 && mid && (
              <View style={styles.map}>
                <KakaoMap center={{ lat: mid[0], lng: mid[1] }} markers={[]} selectedId={null} onSelect={() => {}} path={route} fitPath />
              </View>
            )}
            <View style={styles.stats}>
              <View style={styles.stat}>
                <ThemedText type="small" themeColor="textSecondary">
                  시간
                </ThemedText>
                <ThemedText style={styles.big}>{clock(e.duration_sec ?? 0)}</ThemedText>
              </View>
              <View style={styles.stat}>
                <ThemedText type="small" themeColor="textSecondary">
                  거리
                </ThemedText>
                <ThemedText style={styles.big}>{e.distance_m != null ? distanceLabel(e.distance_m) : '-'}</ThemedText>
              </View>
            </View>
            {e.started_at && (
              <ThemedText type="small" themeColor="textSecondary" style={styles.center}>
                {hm(e.started_at)} ~ {hm(e.ended_at)} · 경로는 나만 볼 수 있어요
              </ThemedText>
            )}
          </>
        )}

        {e?.kind === 'health' && (
          <ThemedView type="backgroundElement" style={styles.card}>
            <Row label="컨디션" value={e.vitality ? `${e.vitality}/5 ${VITALITY_LABEL[e.vitality]}` : null} />
            <Row
              label="식사"
              value={[e.meals_per_day != null ? `하루 ${e.meals_per_day}번` : '', e.meal_amount, e.food].filter(Boolean).join(' · ') || null}
            />
            <Row
              label="약"
              value={e.meds ? (e.meds.length ? e.meds.map((m) => [m.name, m.dose, m.time].filter(Boolean).join(' ')).join('\n') : '먹는 약 없음') : null}
            />
            <Row label="체중" value={e.weight_kg ? `${Number(e.weight_kg)}kg` : null} />
          </ThemedView>
        )}

        {!!e?.content && <ThemedText>{e.content}</ThemedText>}
        {e?.share_in_care_sheet && (
          <ThemedText type="small" themeColor="textSecondary">
            📋 부탁할 때 돌봄 시트에 들어가요
          </ThemedText>
        )}
        {!!e?.images.length && (
          <View style={styles.photos}>
            {e.images.map((img) => (
              <Image key={img.id} source={{ uri: img.url }} style={[styles.photo, { aspectRatio: img.width / img.height }]} contentFit="cover" />
            ))}
          </View>
        )}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.three, paddingBottom: Spacing.six },
  map: { height: 260, borderRadius: 12, overflow: 'hidden' },
  stats: { flexDirection: 'row', gap: Spacing.three },
  stat: { flex: 1, alignItems: 'center', gap: 2 },
  big: { fontSize: 28, lineHeight: 36, fontWeight: 700 },
  center: { textAlign: 'center' },
  card: { borderRadius: 12, padding: Spacing.three, gap: Spacing.two },
  row: { flexDirection: 'row', gap: Spacing.two },
  label: { width: 56 },
  photos: { gap: Spacing.two },
  photo: { width: '100%', borderRadius: 10 },
  headerAction: { paddingHorizontal: Spacing.three },
});
