import { router, Stack, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, Pressable, StyleSheet, View } from 'react-native';

import { ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, type AppNotification, type Page } from '@/lib/api';
import { timeAgo } from '@/lib/format';

export default function Notifications() {
  const theme = useTheme();
  const [items, setItems] = useState<AppNotification[] | null>(null);
  const [next, setNext] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await api<Page<AppNotification>>('/notifications');
      setItems(page.results);
      setNext(page.next);
    } catch (e) {
      setError(e instanceof Error ? e.message : '알림을 불러오지 못했어요.');
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const more = async () => {
    if (!next) return;
    const page = await api<Page<AppNotification>>(next).catch(() => null);
    if (page) {
      setItems((cur) => [...(cur ?? []), ...page.results]);
      setNext(page.next);
    }
  };

  const open = async (n: AppNotification) => {
    if (!n.read_at) {
      api(`/notifications/${n.id}/read`, { method: 'POST' }).catch(() => {});
      setItems((cur) => cur?.map((x) => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)) ?? null);
    }
    if (n.path) router.push(n.path as never);
  };

  const readAll = async () => {
    await api('/notifications/read-all', { method: 'POST' }).catch(() => {});
    load();
  };

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen
        options={{
          headerRight: () =>
            items?.some((n) => !n.read_at) ? (
              <ThemedText type="linkPrimary" onPress={readAll} style={styles.headerAction}>
                모두 읽음
              </ThemedText>
            ) : null,
        }}
      />
      <FlatList
        data={items ?? []}
        keyExtractor={(n) => String(n.id)}
        onEndReached={more}
        onRefresh={load}
        refreshing={false}
        contentContainerStyle={styles.list}
        ListHeaderComponent={<ErrorText message={error} />}
        ListEmptyComponent={
          items ? (
            <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
              아직 알림이 없어요.
            </ThemedText>
          ) : null
        }
        renderItem={({ item: n }) => (
          <Pressable
            accessibilityRole="button"
            onPress={() => open(n)}
            style={({ pressed }) => [
              styles.row,
              { borderColor: theme.border, opacity: pressed ? 0.7 : 1 },
              !n.read_at && { backgroundColor: theme.backgroundElement },
            ]}>
            <View style={styles.flex}>
              <ThemedText type="smallBold">{n.title}</ThemedText>
              {!!n.body && (
                <ThemedText type="small" numberOfLines={2}>
                  {n.body}
                </ThemedText>
              )}
              <ThemedText type="small" themeColor="textSecondary">
                {timeAgo(n.created_at)}
              </ThemedText>
            </View>
            {!n.read_at && <View style={[styles.dot, { backgroundColor: theme.primary }]} />}
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
  dot: { width: 8, height: 8, borderRadius: 4 },
  empty: { textAlign: 'center', marginTop: Spacing.five },
  headerAction: { paddingHorizontal: Spacing.three },
});
