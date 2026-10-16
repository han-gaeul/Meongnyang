import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { useUnread } from '@/hooks/use-unread';

function IconButton({ glyph, count, label, onPress }: { glyph: string; count: number; label: string; onPress: () => void }) {
  const theme = useTheme();
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={count ? `${label} ${count}개` : label} onPress={onPress} style={styles.btn} hitSlop={8}>
      <Text style={styles.glyph}>{glyph}</Text>
      {count > 0 && (
        <View style={[styles.badge, { backgroundColor: theme.danger }]}>
          <ThemedText style={styles.badgeText}>{count > 99 ? '99+' : count}</ThemedText>
        </View>
      )}
    </Pressable>
  );
}

/** 홈 상단: 쪽지함·알림 (안 읽은 수 배지) */
export function InboxButtons() {
  const unread = useUnread();
  return (
    <View style={styles.row}>
      <IconButton glyph="✉️" label="쪽지" count={unread.messages} onPress={() => router.push('/messages')} />
      <IconButton glyph="🔔" label="알림" count={unread.notifications} onPress={() => router.push('/notifications')} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: Spacing.three },
  btn: { padding: 2 },
  glyph: { fontSize: 22 },
  badge: { position: 'absolute', top: -4, right: -8, minWidth: 18, height: 18, borderRadius: 9, paddingHorizontal: 4, alignItems: 'center', justifyContent: 'center' },
  badgeText: { color: '#fff', fontSize: 11, lineHeight: 14, fontWeight: 700 },
});
