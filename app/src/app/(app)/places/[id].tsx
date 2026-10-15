import { Image } from 'expo-image';
import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { Linking, ScrollView, StyleSheet, View } from 'react-native';

import { Button, ErrorText } from '@/components/form';
import { evidenceLine, FitBadge } from '@/components/place-card';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';
import { useTheme } from '@/hooks/use-theme';
import { api, type Page, type Pet, type Place, type PlaceReview } from '@/lib/api';
import { AMENITY_LABEL, daysAgo, distanceLabel, PLACE_CATEGORY_LABEL, SIZE_LABEL, SPACE_LABEL } from '@/lib/format';
import { askReport } from '@/lib/report';

const yn = (v: boolean | null, yes: string, no: string) => (v === null ? '확인 안 됨' : v ? yes : no);

function Cell({ label, value, good }: { label: string; value: string; good?: boolean | null }) {
  const theme = useTheme();
  const unknown = value === '확인 안 됨';
  return (
    <ThemedView type="backgroundElement" style={styles.cell}>
      <ThemedText type="small" themeColor="textSecondary">
        {label}
      </ThemedText>
      <ThemedText
        type="smallBold"
        style={{ color: unknown ? theme.textSecondary : good === false ? theme.danger : good ? theme.primary : theme.text }}>
        {value}
      </ThemedText>
    </ThemedView>
  );
}

function reviewPet(r: PlaceReview) {
  return [
    r.pet_species === 'cat' ? '고양이' : SIZE_LABEL[r.pet_size] ? `${SIZE_LABEL[r.pet_size]}견` : '강아지',
    r.pet_weight_kg ? `${Number(r.pet_weight_kg)}kg` : null,
  ]
    .filter(Boolean)
    .join(' ');
}

export default function PlaceDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const theme = useTheme();
  const { me } = useSession();
  const [place, setPlace] = useState<Place | null>(null);
  const [pet, setPet] = useState<Pet | null>(null);
  const [reviews, setReviews] = useState<PlaceReview[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const pets = (await api<Page<Pet>>('/pets')).results.filter((p) => p.verification_status === 'approved');
      const first = pets[0] ?? null;
      setPet(first);
      setPlace(await api<Place>(`/places/${id}${first ? `?pet=${first.id}` : ''}`));
      setReviews((await api<Page<PlaceReview>>(`/places/${id}/reviews`)).results);
    } catch (e) {
      setError(e instanceof Error ? e.message : '장소를 불러오지 못했어요.');
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  if (!place) {
    return (
      <ThemedView style={[styles.flex, styles.container]}>
        <ErrorText message={error} />
      </ThemedView>
    );
  }

  const c = place.conditions;
  const evidence = evidenceLine(c);
  const isStay = place.category === 'stay';
  const isEat = place.category === 'cafe' || place.category === 'restaurant';
  const policy = [
    place.sizes_allowed.length ? `허용 크기: ${place.sizes_allowed.map((s) => SIZE_LABEL[s]).join('·')}` : null,
    place.max_weight_kg ? `체중 ${place.max_weight_kg}kg까지` : null,
    place.max_pets ? `최대 ${place.max_pets}마리` : null,
    place.restricted_breeds ? `제한 견종: ${place.restricted_breeds}` : null,
    place.fee_per_pet ? `1마리당 ${place.fee_per_pet.toLocaleString()}원` : place.fee_per_pet === 0 ? '추가 요금 없음' : null,
    isStay && place.cats_ok !== null ? (place.cats_ok ? '고양이 동반 가능' : '고양이 동반 불가') : null,
  ].filter(Boolean);

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen options={{ title: PLACE_CATEGORY_LABEL[place.category] }} />
      <ScrollView contentContainerStyle={styles.container}>
        <ErrorText message={error} />

        <View style={styles.section}>
          <View style={styles.row}>
            <ThemedText style={styles.title}>{place.name}</ThemedText>
            <FitBadge fit={place.fit} petName={pet?.name} />
          </View>
          <ThemedText type="small" themeColor="textSecondary">
            {[place.address || place.region_name, distanceLabel(place.distance_m)].filter(Boolean).join(' · ')}
          </ThemedText>
          {place.status === 'pending' && (
            <ThemedText type="small" style={{ color: theme.primary }}>
              운영자 확인 중이에요. 확인되면 다른 사람에게도 보여요.
            </ThemedText>
          )}
        </View>

        <View style={styles.buttons}>
          <View style={styles.flex}>
            <Button title="길찾기" onPress={() => Linking.openURL(place.kakao.directions)} />
          </View>
          {!!place.naver_booking_url && (
            <View style={styles.flex}>
              <Button title="예약 (네이버)" variant="secondary" onPress={() => Linking.openURL(place.naver_booking_url)} />
            </View>
          )}
          {!!place.phone && (
            <View style={styles.flex}>
              <Button title="전화" variant="secondary" onPress={() => Linking.openURL(`tel:${place.phone}`)} />
            </View>
          )}
        </View>
        <ThemedText type="linkPrimary" onPress={() => Linking.openURL(place.kakao.view)}>
          카카오맵에서 보기
        </ThemedText>

        {/* 동반 조건 */}
        {!['hospital', 'pharmacy'].includes(place.category) && (
          <View style={styles.section}>
            <ThemedText type="smallBold">
              동반 조건{c.last_checked ? `  ·  ${daysAgo(c.last_checked)} 확인` : ''}
            </ThemedText>
            <View style={styles.grid}>
              <Cell label="대형견" value={yn(c.large_ok, '가능', '어려워요')} good={c.large_ok} />
              {(isEat || !isStay) && <Cell label="공간" value={c.space ? SPACE_LABEL[c.space] : '확인 안 됨'} />}
              {isEat && <Cell label="바닥" value={yn(c.floor_ok, '내려놔도 돼요', '안기·켄넬 필수')} good={c.floor_ok} />}
              <Cell label="추가 요금" value={yn(c.extra_fee, '있어요', '없어요')} good={c.extra_fee === null ? null : !c.extra_fee} />
            </View>
            {!!evidence && <ThemedText type="small">🐾 {evidence}</ThemedText>}
            {c.differs_from_policy && (
              <ThemedText type="small" style={{ color: theme.danger }}>
                최근 후기가 알려진 정책과 달라요. 방문 전에 전화로 확인해 보세요.
              </ThemedText>
            )}
            {policy.length > 0 && (
              <ThemedText type="small" themeColor="textSecondary">
                {policy.join(' · ')}
              </ThemedText>
            )}
            {place.amenities.length > 0 && (
              <ThemedText type="small" themeColor="textSecondary">
                편의: {place.amenities.map((a) => AMENITY_LABEL[a] ?? a).join(', ')}
              </ThemedText>
            )}
          </View>
        )}

        {(place.is_24h || !!place.hours) && (
          <ThemedView type="backgroundElement" style={styles.card}>
            <ThemedText type="smallBold">🕖 {place.is_24h ? '24시간' : '영업시간'}</ThemedText>
            {!!place.hours && <ThemedText type="small">{place.hours}</ThemedText>}
          </ThemedView>
        )}

        {/* 후기 */}
        <View style={styles.section}>
          <View style={styles.row}>
            <ThemedText type="smallBold">방문 후기 {reviews.length}</ThemedText>
            {me?.is_verified_member && place.status === 'approved' && (
              <ThemedText
                type="linkPrimary"
                accessibilityRole="button"
                onPress={() => router.push({ pathname: '/places/review', params: { place: String(place.id), name: place.name } })}>
                30초 후기 쓰기
              </ThemedText>
            )}
          </View>
          {reviews.length === 0 && (
            <ThemedText type="small" themeColor="textSecondary">
              아직 후기가 없어요. 다녀왔다면 함께 간 아이 기준으로 알려 주세요.
            </ThemedText>
          )}
          {reviews.map((r) => (
            <View key={r.id} style={[styles.review, { borderColor: theme.border }]}>
              <View style={styles.row}>
                <ThemedText type="smallBold">
                  {r.admitted ? '✅ 함께 들어갔어요' : '❌ 못 들어갔어요'}
                </ThemedText>
                {r.is_mine ? (
                  <ThemedText
                    type="small"
                    themeColor="textSecondary"
                    onPress={async () => {
                      await api(`/place-reviews/${r.id}`, { method: 'DELETE' });
                      load();
                    }}>
                    삭제
                  </ThemedText>
                ) : (
                  me?.is_verified_member && (
                    <ThemedText type="small" themeColor="textSecondary" onPress={() => askReport(`/place-reviews/${r.id}/report`, () => load())}>
                      신고
                    </ThemedText>
                  )
                )}
              </View>
              <ThemedText type="small" themeColor="textSecondary">
                {[r.user.nickname, reviewPet(r), r.visited_on.replace(/-/g, '.'), r.verified_visit ? '방문 확인' : null]
                  .filter(Boolean)
                  .join(' · ')}
              </ThemedText>
              <ThemedText type="small">
                {[
                  r.space ? SPACE_LABEL[r.space] : null,
                  r.floor_ok === true ? '바닥 OK' : r.floor_ok === false ? '안기·켄넬 필요' : null,
                  r.extra_fee === false ? '추가요금 없음' : r.extra_fee === true ? '추가요금 있음' : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </ThemedText>
              {!!r.comment && <ThemedText type="small">{r.comment}</ThemedText>}
              {r.images.length > 0 && (
                <View style={styles.photos}>
                  {r.images.map((img) => (
                    <Image key={img.id} source={{ uri: img.url }} style={styles.photo} contentFit="cover" />
                  ))}
                </View>
              )}
            </View>
          ))}
        </View>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.four, paddingBottom: Spacing.six },
  section: { gap: Spacing.two },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: Spacing.two },
  title: { fontSize: 20, lineHeight: 28, fontWeight: 700, flex: 1 },
  buttons: { flexDirection: 'row', gap: Spacing.two },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', rowGap: Spacing.two },
  cell: { borderRadius: 10, paddingVertical: Spacing.two, paddingHorizontal: Spacing.three, width: '48.5%', gap: 2 },
  card: { borderRadius: 12, padding: Spacing.three, gap: Spacing.one },
  review: { borderBottomWidth: StyleSheet.hairlineWidth, paddingBottom: Spacing.three, gap: 4 },
  photos: { flexDirection: 'row', gap: Spacing.two, marginTop: 4 },
  photo: { width: 72, height: 72, borderRadius: 8 },
});
