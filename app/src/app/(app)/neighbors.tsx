import { Stack, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, StyleSheet, View } from 'react-native';

import { ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { openChat } from '@/lib/chat';
import { api, type Neighbor } from '@/lib/api';
import { LEVEL_LABEL } from '@/lib/format';

export default function Neighbors() {
  const theme = useTheme();
  const [items, setItems] = useState<Neighbor[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      api<Neighbor[]>('/neighbors')
        .then(setItems)
        .catch((e) => setError(e instanceof Error ? e.message : '불러오지 못했어요.'));
    }, []),
  );

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen options={{ title: '내 이웃' }} />
      <FlatList
        data={items ?? []}
        keyExtractor={(n) => String(n.id)}
        contentContainerStyle={styles.container}
        ListHeaderComponent={
          <View style={styles.header}>
            <ThemedText type="small" themeColor="textSecondary">
              QR로 만남을 인증한 이웃이에요. 1번 만나면 짧은 부탁을 서로 할 수 있고, 3번 만나고 짧은 부탁을 한 번 함께 마치면 단골 이웃이 되어 집 방문 부탁도 할 수 있어요.
            </ThemedText>
            <ErrorText message={error} />
          </View>
        }
        ListEmptyComponent={
          items ? (
            <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
              아직 만난 이웃이 없어요. 산책 모임에 참여해 보세요.
            </ThemedText>
          ) : null
        }
        renderItem={({ item }) => (
          <View style={[styles.row, { borderColor: theme.border }]}>
            <View style={styles.flex}>
              <ThemedText type="smallBold">{item.nickname}</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                {item.meet_count}번 만남{item.favors_done ? ` · 부탁 ${item.favors_done}번` : ''} · 마지막 {item.last_met_on.replace(/-/g, '.')}
              </ThemedText>
            </View>
            <ThemedText type="linkPrimary" accessibilityRole="button" onPress={() => openChat({ id: item.id, nickname: item.nickname })}>
              쪽지
            </ThemedText>
            <ThemedView type="backgroundElement" style={styles.badge}>
              <ThemedText
                type="smallBold"
                style={{ color: item.level === 'regular' ? theme.primary : theme.text }}>
                {LEVEL_LABEL[item.level]}
              </ThemedText>
            </ThemedView>
          </View>
        )}
      />
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four },
  header: { gap: Spacing.two, marginBottom: Spacing.two },
  empty: { textAlign: 'center', marginTop: Spacing.five },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    paddingVertical: Spacing.three,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  badge: { borderRadius: 999, paddingHorizontal: Spacing.three, paddingVertical: 4 },
});
