import { StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import type { CareSheet } from '@/lib/api';
import { SIZE_LABEL } from '@/lib/format';

function Row({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <View style={styles.row}>
      <ThemedText type="small" themeColor="textSecondary" style={styles.label}>
        {label}
      </ThemedText>
      <ThemedText type="small" style={styles.value}>
        {value}
      </ThemedText>
    </View>
  );
}

const yesNo = (v: boolean | null, yes: string, no: string) => (v === null ? '' : v ? yes : no);

/** 돌봄 시트 전체 (보호자·맡은 이웃용) */
export function CareSheetView({ sheet }: { sheet: CareSheet }) {
  const b = sheet.basic;
  const basic = [
    b.breed,
    b.sex === 'M' ? '남아' : b.sex === 'F' ? '여아' : '',
    b.age !== null ? `${b.age}살` : '',
    SIZE_LABEL[b.size as keyof typeof SIZE_LABEL] ?? '',
    b.weight_kg ? `${b.weight_kg}kg` : '',
    yesNo(b.neutered, '중성화 O', '중성화 X'),
    yesNo(b.vaccinated, '접종 완료', '접종 미완료'),
  ]
    .filter(Boolean)
    .join(' · ');
  const meal = [
    sheet.meal.times_per_day !== null ? `하루 ${sheet.meal.times_per_day}번` : '',
    sheet.meal.amount,
    sheet.meal.food,
  ]
    .filter(Boolean)
    .join(' · ');
  const walk = [
    sheet.walk.minutes !== null ? `한 번에 ${sheet.walk.minutes}분` : '',
    sheet.walk.per_week !== null ? `주 ${sheet.walk.per_week}회` : '',
  ]
    .filter(Boolean)
    .join(' · ');
  const meds = sheet.meds.map((m) => [m.name, m.dose, m.time].filter(Boolean).join(' ')).join('\n');

  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedText type="smallBold">🗒 {b.name} 돌봄 시트</ThemedText>
      <Row label="기본" value={basic} />
      <Row label="성격" value={b.traits.join(', ')} />
      <Row label="식사" value={meal} />
      <Row label="약" value={meds} />
      <Row label="산책" value={walk} />
      <Row label="컨디션" value={sheet.condition} />
      <Row label="특이사항" value={sheet.notes} />
      <Row label="주의할 점" value={sheet.caution} />
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 12, padding: Spacing.three, gap: Spacing.two },
  row: { flexDirection: 'row', gap: Spacing.two },
  label: { width: 64 },
  value: { flex: 1 },
});
