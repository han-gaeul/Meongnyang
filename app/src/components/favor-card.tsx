import { router } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { Favor } from '@/lib/api';
import { FAVOR_KIND_LABEL, FAVOR_STATUS_LABEL, minutesLabel, SIZE_LABEL, whenLabel } from '@/lib/format';

export function FavorCard({ favor: f }: { favor: Favor }) {
  const theme = useTheme();
  const s = f.care_summary;
  const pet = [f.pet.name, s.breed, SIZE_LABEL[s.size as keyof typeof SIZE_LABEL] ?? ''].filter(Boolean).join(' · ');
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push({ pathname: '/favors/[id]', params: { id: String(f.id) } })}
      style={({ pressed }) => [styles.card, { borderColor: theme.border, opacity: pressed ? 0.7 : 1 }]}>
      <View style={styles.top}>
        <View style={styles.badges}>
          <ThemedView type="backgroundElement" style={styles.badge}>
            <ThemedText type="small">{FAVOR_KIND_LABEL[f.kind]}</ThemedText>
          </ThemedView>
          {f.visit_home && (
            <ThemedView type="backgroundElement" style={styles.badge}>
              <ThemedText type="small">집 방문</ThemedText>
            </ThemedView>
          )}
        </View>
        <ThemedText type="smallBold" style={{ color: f.status === 'open' ? theme.primary : theme.textSecondary }}>
          {FAVOR_STATUS_LABEL[f.status]}
        </ThemedText>
      </View>
      <ThemedText type="smallBold" numberOfLines={1}>
        {f.title}
      </ThemedText>
      <ThemedText type="small">
        {whenLabel(f.starts_at)} · {minutesLabel(f.duration_minutes)}
        {f.place_name ? ` · ${f.place_name}` : ''}
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {[
          f.requester.nickname,
          pet,
          f.is_requester && f.pending_count ? `신청 ${f.pending_count}` : null,
          f.my_application?.status === 'pending' ? '신청함' : null,
          f.my_application?.status === 'accepted' ? '내가 맡음' : null,
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
  badges: { flexDirection: 'row', gap: Spacing.one },
  badge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 },
});
