import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Chips } from '@/components/chips';
import { ErrorText } from '@/components/form';
import { InboxButtons } from '@/components/inbox-buttons';
import { PostCard } from '@/components/post-card';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';
import { useTheme } from '@/hooks/use-theme';
import { api, type Page, type Post } from '@/lib/api';

type Species = '' | 'dog' | 'cat';

function feedPath(species: Species, q: string) {
  const params = new URLSearchParams();
  if (species) params.set('species', species);
  if (q.trim()) params.set('q', q.trim());
  const qs = params.toString();
  return `/posts${qs ? `?${qs}` : ''}`;
}

export default function Home() {
  const theme = useTheme();
  const { me } = useSession();
  const [species, setSpecies] = useState<Species>('');
  const [query, setQuery] = useState('');
  const [posts, setPosts] = useState<Post[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const load = useCallback(async (s: Species, q: string) => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const page = await api<Page<Post>>(feedPath(s, q));
      if (id !== requestId.current) return; // 필터를 빠르게 바꾼 경우 오래된 응답 무시
      setPosts(page.results);
      setNext(page.next);
    } catch (e) {
      if (id === requestId.current) setError(e instanceof Error ? e.message : '불러오지 못했어요.');
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(species, query);
      // 검색어는 제출할 때만 반영한다
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [load, species]),
  );

  const loadMore = async () => {
    if (!next || loading) return;
    setLoading(true);
    try {
      const page = await api<Page<Post>>(next);
      setPosts((prev) => [...prev, ...page.results]);
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
              {me?.region_name || '우리 동네'}
            </ThemedText>
            <InboxButtons />
          </View>
          <TextInput
            value={query}
            onChangeText={setQuery}
            onSubmitEditing={() => load(species, query)}
            placeholder="글 검색"
            placeholderTextColor={theme.textSecondary}
            returnKeyType="search"
            style={[styles.search, { backgroundColor: theme.backgroundElement, color: theme.text }]}
          />
          <Chips
            value={species}
            onChange={setSpecies}
            options={[
              { value: '', label: '전체' },
              { value: 'dog', label: '강아지' },
              { value: 'cat', label: '고양이' },
            ]}
          />
          {!canWrite && (
            <ThemedText type="small" themeColor="textSecondary">
              둘러보는 중이에요. 마이 탭에서 인증을 마치면 글을 쓸 수 있어요.
            </ThemedText>
          )}
          <ErrorText message={error} />
        </View>

        <FlatList
          data={posts}
          keyExtractor={(p) => String(p.id)}
          renderItem={({ item }) => <PostCard post={item} />}
          contentContainerStyle={styles.list}
          onEndReached={loadMore}
          onEndReachedThreshold={0.5}
          refreshing={refreshing}
          onRefresh={async () => {
            setRefreshing(true);
            await load(species, query);
            setRefreshing(false);
          }}
          ListEmptyComponent={
            loading ? null : (
              <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
                {query ? '검색 결과가 없어요.' : '아직 글이 없어요. 첫 글을 남겨 보세요.'}
              </ThemedText>
            )
          }
          ListFooterComponent={loading && !refreshing ? <ActivityIndicator style={styles.spinner} /> : null}
        />

        {canWrite && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="글쓰기"
            onPress={() => router.push('/posts/new')}
            style={({ pressed }) => [styles.fab, { backgroundColor: theme.primary, opacity: pressed ? 0.85 : 1 }]}>
            <ThemedText type="smallBold" style={{ color: theme.onPrimary }}>
              + 글쓰기
            </ThemedText>
          </Pressable>
        )}
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  flex: { flex: 1 },
  header: { paddingHorizontal: Spacing.four, paddingTop: Spacing.two, paddingBottom: Spacing.two, gap: Spacing.two },
  title: { fontSize: 24, lineHeight: 32 },
  search: { borderRadius: 10, paddingHorizontal: Spacing.three, paddingVertical: 10, fontSize: 15 },
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
