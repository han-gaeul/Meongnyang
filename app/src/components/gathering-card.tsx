import { router } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { Gathering } from '@/lib/api';
import { GATHERING_STATUS_LABEL, KIND_LABEL, SPECIES_LABEL, whenLabel } from '@/lib/format';

export function GatheringCard({ gathering: g }: { gathering: Gathering }) {
  const theme = useTheme();
  const open = g.status === 'open';
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push({ pathname: '/gatherings/[id]', params: { id: String(g.id) } })}
      style={({ pressed }) => [styles.card, { borderColor: theme.border, opacity: pressed ? 0.7 : 1 }]}>
      <View style={styles.top}>
        <ThemedView type="backgroundElement" style={styles.badge}>
          <ThemedText type="small">{KIND_LABEL[g.kind]}</ThemedText>
        </ThemedView>
        <ThemedText type="smallBold" style={{ color: open ? theme.primary : theme.textSecondary }}>
          {GATHERING_STATUS_LABEL[g.status]}
        </ThemedText>
      </View>
      <ThemedText type="smallBold" numberOfLines={1}>
        {g.title}
      </ThemedText>
      <ThemedText type="small">
        {whenLabel(g.starts_at)} · {g.place_name}
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {[
          g.host.nickname,
          g.species !== 'all' ? SPECIES_LABEL[g.species] : null,
          `${g.accepted_count}/${g.capacity}명`,
          g.my_participation?.status === 'accepted' ? '참여 중' : null,
          g.my_participation?.status === 'pending' ? '신청함' : null,
          g.is_host ? '내 모임' : null,
        ]
          .filter(Boolean)
          .join(' · ')}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { paddingVertical: Spacing.three, borderBottomWidth: StyleSheet.hairlineWidth, gap: 4 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  badge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 },
});
