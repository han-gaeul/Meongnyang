import { Pressable, ScrollView, StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export function Chips<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  const theme = useTheme();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.scroll}
      contentContainerStyle={styles.row}>
      {options.map((o) => {
        const selected = o.value === value;
        return (
          <Pressable
            key={o.value}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            onPress={() => onChange(o.value)}
            style={[
              styles.chip,
              {
                borderColor: selected ? theme.primary : theme.border,
                backgroundColor: selected ? theme.primary : 'transparent',
              },
            ]}>
            <ThemedText type="small" style={{ color: selected ? theme.onPrimary : theme.text }}>
              {o.label}
            </ThemedText>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

/** 여러 개를 켜고 끄는 칩 (필터용) */
export function ToggleChips<T extends string>({
  values,
  options,
  onChange,
}: {
  values: T[];
  options: { value: T; label: string }[];
  onChange: (v: T[]) => void;
}) {
  const theme = useTheme();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.scroll} contentContainerStyle={styles.row}>
      {options.map((o) => {
        const on = values.includes(o.value);
        return (
          <Pressable
            key={o.value}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: on }}
            onPress={() => onChange(on ? values.filter((v) => v !== o.value) : [...values, o.value])}
            style={[
              styles.chip,
              { borderColor: on ? theme.primary : theme.border, backgroundColor: on ? theme.primary : 'transparent' },
            ]}>
            <ThemedText type="small" style={{ color: on ? theme.onPrimary : theme.text }}>
              {o.label}
            </ThemedText>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // 세로로 남는 공간을 차지하지 않도록 (flex 부모 안에서 늘어나는 문제 방지)
  scroll: { flexGrow: 0 },
  row: { gap: Spacing.two },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: Spacing.three, paddingVertical: 6 },
});
