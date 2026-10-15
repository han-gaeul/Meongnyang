import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, Pressable, StyleSheet, View } from 'react-native';

import { ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, type Thread } from '@/lib/api';
import { timeAgo } from '@/lib/format';

/** 쪽지함: 상대별 마지막 쪽지 */
export default function Inbox() {
  const theme = useTheme();
  const [items, setItems] = useState<Thread[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api<Thread[]>('/messages/threads'));
    } catch (e) {
      setError(e instanceof Error ? e.message : '쪽지를 불러오지 못했어요.');
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  return (
    <ThemedView style={styles.flex}>
      <FlatList
        data={items ?? []}
        keyExtractor={(t) => String(t.user.id)}
        onRefresh={load}
        refreshing={false}
        contentContainerStyle={styles.list}
        ListHeaderComponent={<ErrorText message={error} />}
        ListEmptyComponent={
          items ? (
            <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
              주고받은 쪽지가 없어요.{'\n'}만남 인증을 한 이웃이나 같은 모임·부탁의 이웃에게 보낼 수 있어요.
            </ThemedText>
          ) : null
        }
        renderItem={({ item: t }) => (
          <Pressable
            accessibilityRole="button"
            onPress={() => router.push({ pathname: '/messages/[userId]', params: { userId: String(t.user.id), name: t.user.nickname } })}
            style={({ pressed }) => [styles.row, { borderColor: theme.border, opacity: pressed ? 0.7 : 1 }]}>
            <View style={styles.flex}>
              <View style={styles.top}>
                <ThemedText type="smallBold">{t.user.nickname}</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  {timeAgo(t.last.created_at)}
                </ThemedText>
              </View>
              <ThemedText type="small" numberOfLines={1} themeColor={t.unread ? undefined : 'textSecondary'}>
                {t.last.is_mine ? '나: ' : ''}
                {t.last.content}
              </ThemedText>
            </View>
            {t.unread > 0 && (
              <View style={[styles.badge, { backgroundColor: theme.primary }]}>
                <ThemedText style={styles.badgeText}>{t.unread}</ThemedText>
              </View>
            )}
          </Pressable>
        )}
      />
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  list: { paddingBottom: Spacing.six },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.three,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  top: { flexDirection: 'row', justifyContent: 'space-between' },
  badge: { minWidth: 20, height: 20, borderRadius: 10, paddingHorizontal: 6, alignItems: 'center', justifyContent: 'center' },
  badgeText: { color: '#fff', fontSize: 12, lineHeight: 16, fontWeight: 700 },
  empty: { textAlign: 'center', marginTop: Spacing.five, paddingHorizontal: Spacing.four },
});
