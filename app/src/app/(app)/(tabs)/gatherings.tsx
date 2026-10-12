import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Chips } from '@/components/chips';
import { ErrorText } from '@/components/form';
import { FavorCard } from '@/components/favor-card';
import { GatheringCard } from '@/components/gathering-card';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';
import { useTheme } from '@/hooks/use-theme';
import { api, type Favor, type Gathering, type Page } from '@/lib/api';

type Tab = 'walk' | 'share' | 'favor' | 'mine' | 'myfavor';
type Item = { type: 'gathering'; data: Gathering } | { type: 'favor'; data: Favor };

const isFavorTab = (t: Tab) => t === 'favor' || t === 'myfavor';

function listPath(tab: Tab) {
  if (tab === 'favor') return '/favors';
  if (tab === 'myfavor') return '/favors?mine=1';
  return tab === 'mine' ? '/gatherings?mine=1' : `/gatherings?kind=${tab}`;
}

function wrap(tab: Tab, rows: (Gathering | Favor)[]): Item[] {
  return isFavorTab(tab)
    ? rows.map((r) => ({ type: 'favor', data: r as Favor }))
    : rows.map((r) => ({ type: 'gathering', data: r as Gathering }));
}

export default function Gatherings() {
  const theme = useTheme();
  const { me } = useSession();
  const [tab, setTab] = useState<Tab>('walk');
  const [items, setItems] = useState<Item[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const load = useCallback(async (t: Tab) => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const page = await api<Page<Gathering | Favor>>(listPath(t));
      if (id !== requestId.current) return;
      setItems(wrap(t, page.results));
      setNext(page.next);
    } catch (e) {
      if (id === requestId.current) setError(e instanceof Error ? e.message : '불러오지 못했어요.');
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(tab);
    }, [load, tab]),
  );

  const loadMore = async () => {
    if (!next || loading) return;
    setLoading(true);
    try {
      const page = await api<Page<Gathering | Favor>>(next);
      setItems((prev) => [...prev, ...wrap(tab, page.results)]);
      setNext(page.next);
    } catch (e) {
      setError(e instanceof Error ? e.message : '불러오지 못했어요.');
    } finally {
      setLoading(false);
    }
  };

  const canWrite = !!me?.is_verified_member;

  return (
    <ThemedView style={styles.flex}>
      <SafeAreaView style={styles.flex} edges={['top']}>
        <View style={styles.header}>
          <View style={styles.titleRow}>
            <ThemedText type="subtitle" style={styles.title}>
              모임·부탁
            </ThemedText>
            {canWrite && (
              <ThemedText type="linkPrimary" accessibilityRole="button" onPress={() => router.push('/meetup')}>
                만남 인증 QR
              </ThemedText>
            )}
          </View>
          <Chips
            value={tab}
            onChange={setTab}
            options={[
              { value: 'walk', label: '산책' },
              { value: 'share', label: '나눔' },
              { value: 'favor', label: '이웃 부탁' },
              { value: 'mine', label: '내 모임' },
              { value: 'myfavor', label: '내 부탁' },
            ]}
          />
          {!canWrite && (
            <ThemedText type="small" themeColor="textSecondary">
              둘러보는 중이에요. 인증을 마치면 모임에 참여하고 만들 수 있어요.
            </ThemedText>
          )}
          <ErrorText message={error} />
        </View>

        <FlatList
          data={items}
          keyExtractor={(it) => `${it.type}-${it.data.id}`}
          renderItem={({ item }) =>
            item.type === 'favor' ? <FavorCard favor={item.data} /> : <GatheringCard gathering={item.data} />
          }
          contentContainerStyle={styles.list}
          onEndReached={loadMore}
          onEndReachedThreshold={0.5}
          refreshing={refreshing}
          onRefresh={async () => {
            setRefreshing(true);
            await load(tab);
            setRefreshing(false);
          }}
          ListEmptyComponent={
            loading ? null : (
              <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
                {
                  {
                    walk: '예정된 산책 모임이 없어요. 먼저 모임을 열어 보세요.',
                    share: '진행 중인 나눔이 없어요. 남는 사료·용품을 나눠 보세요.',
                    favor: '이웃의 부탁이 없어요. 만남 인증을 한 이웃의 부탁만 여기 보여요.',
                    mine: '아직 연 모임이나 참여한 모임이 없어요.',
                    myfavor: '아직 올리거나 맡은 부탁이 없어요. 만난 이웃에게 짧은 부탁을 해 보세요.',
                  }[tab]
                }
              </ThemedText>
            )
          }
          ListFooterComponent={loading && !refreshing ? <ActivityIndicator style={styles.spinner} /> : null}
        />

        {canWrite && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={isFavorTab(tab) ? '부탁하기' : '모임 만들기'}
            onPress={() =>
              isFavorTab(tab)
                ? router.push('/favors/new')
                : router.push({ pathname: '/gatherings/new', params: { kind: tab === 'share' ? 'share' : 'walk' } })
            }
            style={({ pressed }) => [styles.fab, { backgroundColor: theme.primary, opacity: pressed ? 0.85 : 1 }]}>
            <ThemedText type="smallBold" style={{ color: theme.onPrimary }}>
              + {isFavorTab(tab) ? '부탁하기' : tab === 'share' ? '나눔하기' : '모임 열기'}
            </ThemedText>
          </Pressable>
        )}
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: { paddingHorizontal: Spacing.four, paddingTop: Spacing.two, paddingBottom: Spacing.two, gap: Spacing.two },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 24, lineHeight: 32 },
  list: { paddingHorizontal: Spacing.four, paddingBottom: 96 },
  empty: { textAlign: 'center', marginTop: Spacing.five },
  spinner: { marginVertical: Spacing.three },
  fab: {
    position: 'absolute',
    right: Spacing.four,
    bottom: Spacing.four,
    borderRadius: 999,
    paddingHorizontal: Spacing.four,
    paddingVertical: 14,
    elevation: 3,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
  },
});
