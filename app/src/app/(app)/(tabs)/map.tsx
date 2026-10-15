import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Chips, ToggleChips } from '@/components/chips';
import { ErrorText } from '@/components/form';
import { KakaoMap, kakaoMapAvailable, type MapMarker } from '@/components/kakao-map';
import { PlaceCard } from '@/components/place-card';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';
import { useTheme } from '@/hooks/use-theme';
import { api, type Page, type Pet, type Place } from '@/lib/api';
import { getCurrentCoords, type Coords } from '@/lib/location';

const CATEGORIES = [
  { value: 'all', label: '전체', q: '' },
  { value: 'eat', label: '카페·식당', q: 'cafe,restaurant' },
  { value: 'stay', label: '숙소', q: 'stay' },
  { value: 'park', label: '공원·관광지', q: 'park,attraction' },
  { value: 'vet', label: '병원·약국', q: 'hospital,pharmacy' },
  { value: 'care', label: '미용·위탁', q: 'grooming,hotel' },
] as const;
type Cat = (typeof CATEGORIES)[number]['value'];

type Filter = 'fit' | 'large' | 'indoor' | 'floor' | 'nofee' | '24h';

// 위치를 못 받으면 서울시청 근처로 시작
const FALLBACK: Coords = { lat: 37.5665, lng: 126.978 };

/** 현재 위치 → 내 동네 좌표 → 기본값 순서 */
async function resolveCenter(homeLat: number | null, homeLng: number | null): Promise<{ coords: Coords; note: string | null }> {
  try {
    return { coords: await getCurrentCoords(), note: null };
  } catch (e) {
    if (homeLat != null && homeLng != null) {
      return { coords: { lat: homeLat, lng: homeLng }, note: '현재 위치를 몰라 내 동네 기준으로 보여드려요.' };
    }
    return { coords: FALLBACK, note: e instanceof Error ? e.message : '위치를 알 수 없어요.' };
  }
}

function sameArea(a: Coords, b: Coords) {
  return Math.abs(a.lat - b.lat) < 0.002 && Math.abs(a.lng - b.lng) < 0.0025; // 약 200m
}

export default function MapTab() {
  const theme = useTheme();
  const { me } = useSession();
  const [center, setCenter] = useState<Coords | null>(null);
  const [moved, setMoved] = useState<Coords | null>(null);
  const [locNote, setLocNote] = useState<string | null>(null);
  const [cat, setCat] = useState<Cat>('all');
  const [filters, setFilters] = useState<Filter[]>([]);
  const [pets, setPets] = useState<Pet[]>([]);
  const [petId, setPetId] = useState('');
  const [items, setItems] = useState<Place[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const list = useRef<FlatList<Place>>(null);
  const requestId = useRef(0);

  const homeLat = me?.latitude ?? null;
  const homeLng = me?.longitude ?? null;

  const locate = useCallback(() => {
    resolveCenter(homeLat, homeLng).then(({ coords, note }) => {
      setCenter(coords);
      setLocNote(note);
      setMoved(null);
    });
  }, [homeLat, homeLng]);

  useEffect(() => {
    let alive = true;
    resolveCenter(homeLat, homeLng).then(({ coords, note }) => {
      if (!alive) return;
      setCenter(coords);
      setLocNote(note);
    });
    return () => {
      alive = false;
    };
  }, [homeLat, homeLng]);

  useFocusEffect(
    useCallback(() => {
      api<Page<Pet>>('/pets')
        .then((page) => {
          const ok = page.results.filter((p) => p.verification_status === 'approved');
          setPets(ok);
          setPetId((cur) => cur || (ok[0] ? String(ok[0].id) : ''));
        })
        .catch(() => setPets([]));
    }, []),
  );

  const pet = pets.find((p) => String(p.id) === petId);

  const load = useCallback(async () => {
    if (!center) return;
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    const q = new URLSearchParams({ lat: String(center.lat), lng: String(center.lng), radius: '5000' });
    const category = CATEGORIES.find((c) => c.value === cat)!.q;
    if (category) q.set('category', category);
    if (petId) q.set('pet', petId);
    if (petId && filters.includes('fit')) q.set('fit', '1');
    const chips = filters.filter((f) => f !== 'fit');
    if (chips.length) q.set('chips', chips.join(','));
    try {
      const data = await api<Place[]>(`/places?${q.toString()}`);
      if (id !== requestId.current) return;
      setItems(data);
      setSelected(null);
    } catch (e) {
      if (id === requestId.current) setError(e instanceof Error ? e.message : '장소를 불러오지 못했어요.');
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [center, cat, filters, petId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const markers: MapMarker[] = useMemo(
    () => (items ?? []).map((p) => ({ id: p.id, lat: p.lat, lng: p.lng, label: p.name.replace(/^\[샘플\]\s*/, ''), tone: pet ? p.fit : 'unknown' })),
    [items, pet],
  );

  const select = (id: number) => {
    setSelected(id);
    const index = (items ?? []).findIndex((p) => p.id === id);
    if (index >= 0) list.current?.scrollToIndex({ index, viewPosition: 0, animated: true });
  };

  const filterOptions: { value: Filter; label: string }[] = [
    ...(pet ? [{ value: 'fit' as const, label: `${pet.name} OK인 곳` }] : []),
    { value: 'large', label: '대형견 OK' },
    { value: 'indoor', label: '실내 OK' },
    { value: 'floor', label: '바닥 OK' },
    { value: 'nofee', label: '추가요금 없음' },
    { value: '24h', label: '24시' },
  ];

  return (
    <ThemedView style={styles.flex}>
      <SafeAreaView style={styles.flex} edges={['top']}>
        <View style={styles.header}>
          <View style={styles.titleRow}>
            <ThemedText type="subtitle" style={styles.title}>
              동네 지도
            </ThemedText>
            {me?.is_verified_member && (
              <ThemedText type="linkPrimary" accessibilityRole="button" onPress={() => router.push('/places/new')}>
                + 장소 제보
              </ThemedText>
            )}
          </View>
          <Chips value={cat} onChange={setCat} options={CATEGORIES.map(({ value, label }) => ({ value, label }))} />
          <ToggleChips values={filters} onChange={setFilters} options={filterOptions} />
          {pets.length > 1 && (
            <Chips value={petId} onChange={setPetId} options={pets.map((p) => ({ value: String(p.id), label: `${p.name} 기준` }))} />
          )}
          {!!locNote && (
            <ThemedText type="small" themeColor="textSecondary">
              {locNote}
            </ThemedText>
          )}
          <ErrorText message={error} />
        </View>

        {kakaoMapAvailable && center && (
          <View style={styles.map}>
            <KakaoMap center={center} markers={markers} selectedId={selected} onSelect={select} onMove={(c) => !sameArea(c, center) && setMoved(c)} />
            {moved && (
              <Pressable
                accessibilityRole="button"
                onPress={() => {
                  setCenter(moved);
                  setMoved(null);
                }}
                style={[styles.reSearch, { backgroundColor: theme.background, borderColor: theme.border }]}>
                <ThemedText type="smallBold">이 지역에서 다시 찾기</ThemedText>
              </Pressable>
            )}
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="내 위치로"
              onPress={locate}
              style={[styles.myLoc, { backgroundColor: theme.background, borderColor: theme.border }]}>
              <ThemedText>◎</ThemedText>
            </Pressable>
          </View>
        )}

        <FlatList
          ref={list}
          data={items ?? []}
          keyExtractor={(p) => String(p.id)}
          renderItem={({ item }) => <PlaceCard place={item} petName={pet?.name} selected={item.id === selected} />}
          contentContainerStyle={styles.list}
          onScrollToIndexFailed={() => {}}
          refreshing={false}
          onRefresh={load}
          ListHeaderComponent={
            !kakaoMapAvailable && items ? (
              <ThemedText type="small" themeColor="textSecondary" style={styles.note}>
                반경 5km · 가까운 순 {items.length}곳
              </ThemedText>
            ) : null
          }
          ListEmptyComponent={
            loading || !items ? (
              <ActivityIndicator style={styles.spinner} />
            ) : (
              <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
                {filters.length ? '조건에 맞는 곳이 없어요. 필터를 줄여 보세요.' : '근처에 등록된 장소가 없어요. 아는 곳을 제보해 주세요.'}
              </ThemedText>
            )
          }
        />
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: { paddingHorizontal: Spacing.four, paddingTop: Spacing.two, paddingBottom: Spacing.two, gap: Spacing.two },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 24, lineHeight: 32 },
  map: { height: 300 },
  reSearch: {
    position: 'absolute',
    top: Spacing.two,
    alignSelf: 'center',
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: Spacing.three,
    paddingVertical: 8,
  },
  myLoc: {
    position: 'absolute',
    right: Spacing.two,
    bottom: Spacing.two,
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  list: { paddingHorizontal: Spacing.three, paddingBottom: Spacing.six },
  note: { paddingHorizontal: Spacing.two, paddingVertical: Spacing.one },
  empty: { textAlign: 'center', marginTop: Spacing.five, paddingHorizontal: Spacing.four },
  spinner: { marginVertical: Spacing.four },
});
