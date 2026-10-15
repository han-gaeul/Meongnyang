import { router } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { Place, PlaceConditions } from '@/lib/api';
import { daysAgo, distanceLabel, PLACE_CATEGORY_LABEL, SPACE_LABEL } from '@/lib/format';

/** "대형견 OK · 실내 OK · 바닥 OK · 추가요금 없음" (확인된 것만) */
export function conditionLine(c: PlaceConditions): string {
  return [
    c.large_ok === true ? '대형견 OK' : c.large_ok === false ? '대형견 X' : null,
    c.space ? SPACE_LABEL[c.space] : null,
    c.floor_ok === true ? '바닥 OK' : c.floor_ok === false ? '안기·켄넬 필수' : null,
    c.extra_fee === false ? '추가요금 없음' : c.extra_fee === true ? '추가요금 있음' : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

/** "대형견 후기 2건 · 최대 32kg" */
export function evidenceLine(c: PlaceConditions): string {
  if (!c.review_count) return '';
  return [
    c.large_reviews ? `대형견 후기 ${c.large_reviews}건` : `후기 ${c.review_count}건`,
    c.max_weight_admitted ? `최대 ${c.max_weight_admitted}kg` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

export function FitBadge({ fit, petName }: { fit: Place['fit']; petName?: string }) {
  const theme = useTheme();
  if (!petName) return null;
  const label = { yes: `${petName} OK`, no: `${petName} 어려워요`, unknown: '확인 필요' }[fit];
  const bg = fit === 'yes' ? theme.primary : 'transparent';
  const color = fit === 'yes' ? theme.onPrimary : theme.textSecondary;
  return (
    <View style={[styles.badge, { backgroundColor: bg, borderColor: fit === 'yes' ? theme.primary : theme.border }]}>
      <ThemedText type="small" style={{ color, fontWeight: fit === 'yes' ? 700 : 400 }}>
        {label}
      </ThemedText>
    </View>
  );
}

export function PlaceCard({
  place: p,
  petName,
  selected,
  onPress,
}: {
  place: Place;
  petName?: string;
  selected?: boolean;
  onPress?: () => void;
}) {
  const theme = useTheme();
  const cond = conditionLine(p.conditions);
  const evidence = evidenceLine(p.conditions);
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress ?? (() => router.push({ pathname: '/places/[id]', params: { id: String(p.id) } }))}
      style={({ pressed }) => [
        styles.card,
        { borderColor: theme.border, opacity: pressed ? 0.7 : 1 },
        selected && { backgroundColor: theme.backgroundElement },
      ]}>
      <View style={styles.top}>
        <ThemedText type="smallBold" numberOfLines={1} style={styles.name}>
          {p.name}
        </ThemedText>
        <FitBadge fit={p.fit} petName={petName} />
      </View>
      <ThemedText type="small" themeColor="textSecondary">
        {[PLACE_CATEGORY_LABEL[p.category], distanceLabel(p.distance_m), p.is_24h ? '24시' : null].filter(Boolean).join(' · ')}
        {p.status === 'pending' ? ' · 검토 중' : ''}
      </ThemedText>
      {!!cond && <ThemedText type="small">{cond}</ThemedText>}
      {(!!evidence || !!p.conditions.last_checked) && (
        <ThemedText type="small" themeColor="textSecondary">
          {[evidence, p.conditions.last_checked ? `${daysAgo(p.conditions.last_checked)} 확인` : null]
            .filter(Boolean)
            .join(' · ')}
        </ThemedText>
      )}
      {!cond && !evidence && (
        <ThemedView type="backgroundElement" style={styles.hint}>
          <ThemedText type="small" themeColor="textSecondary">
            동반 조건을 아직 몰라요. 다녀왔다면 30초 후기를 남겨 주세요.
          </ThemedText>
        </ThemedView>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { paddingVertical: Spacing.three, paddingHorizontal: Spacing.two, borderBottomWidth: StyleSheet.hairlineWidth, gap: 4, borderRadius: 8 },
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: Spacing.two },
  name: { flex: 1 },
  badge: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 1 },
  hint: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, alignSelf: 'flex-start' },
});
