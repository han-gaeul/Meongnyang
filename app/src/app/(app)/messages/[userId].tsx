import { Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActionSheetIOS, Alert, FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, type Message, type Page } from '@/lib/api';
import { askReport } from '@/lib/report';

const POLL_MS = 10_000;

function timeLabel(iso: string) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/** 한 사람과 주고받은 쪽지 */
export default function Conversation() {
  const { userId, name } = useLocalSearchParams<{ userId: string; name?: string }>();
  const theme = useTheme();
  const [items, setItems] = useState<Message[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [blocked, setBlocked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState(name ?? '');

  const load = useCallback(async () => {
    try {
      const page = await api<Page<Message>>(`/messages?with=${userId}`);
      setItems(page.results);
      setNext(page.next);
      const other = page.results[0] && (page.results[0].is_mine ? page.results[0].recipient : page.results[0].sender);
      if (other) setTitle(other.nickname);
      if (page.results.some((m) => !m.is_mine && !m.read_at)) {
        api('/messages/read', { method: 'POST', body: { user: Number(userId) } }).catch(() => {});
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '쪽지를 불러오지 못했어요.');
    }
  }, [userId]);

  useFocusEffect(
    useCallback(() => {
      load();
      api<{ ok: boolean; reason: string }>(`/messages/can-send?to=${userId}`)
        .then((r) => setBlocked(r.ok ? null : r.reason))
        .catch(() => {});
      // 상대 답장을 보려고 화면이 열려 있는 동안만 가볍게 새로 고침 (실시간 채팅은 1.1에서)
      const timer = setInterval(load, POLL_MS);
      return () => clearInterval(timer);
    }, [load, userId]),
  );

  const more = async () => {
    if (!next) return;
    const page = await api<Page<Message>>(next).catch(() => null);
    if (page) {
      setItems((cur) => [...cur, ...page.results]);
      setNext(page.next);
    }
  };

  const send = async () => {
    const content = text.trim();
    if (!content) return;
    setSending(true);
    setError(null);
    try {
      const m = await api<Message>('/messages/send', { method: 'POST', body: { recipient: Number(userId), content } });
      setItems((cur) => [m, ...cur]);
      setText('');
    } catch (e) {
      setError(e instanceof Error ? e.message : '보내지 못했어요.');
    } finally {
      setSending(false);
    }
  };

  const remove = async (m: Message) => {
    await api(`/messages/${m.id}`, { method: 'DELETE' }).catch(() => {});
    setItems((cur) => cur.filter((x) => x.id !== m.id));
  };

  const menu = (m: Message) => {
    const options = m.is_mine ? ['내 쪽에서 지우기', '닫기'] : ['내 쪽에서 지우기', '신고하기', '닫기'];
    const pick = (i: number) => {
      if (i === 0) remove(m);
      if (!m.is_mine && i === 1) askReport(`/messages/${m.id}/report`, () => setItems((cur) => cur.filter((x) => x.id !== m.id)));
    };
    if (Platform.OS === 'ios') {
      ActionSheetIOS.showActionSheetWithOptions(
        { options, cancelButtonIndex: options.length - 1, destructiveButtonIndex: m.is_mine ? undefined : 1 },
        pick,
      );
    } else {
      Alert.alert('쪽지', undefined, options.map((text, i) => ({ text, onPress: () => pick(i), style: i === options.length - 1 ? 'cancel' : 'default' })));
    }
  };

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen options={{ title }} />
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
        <FlatList
          inverted
          data={items}
          keyExtractor={(m) => String(m.id)}
          onEndReached={more}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
              첫 쪽지를 보내 보세요.
            </ThemedText>
          }
          renderItem={({ item: m }) => (
            <Pressable onLongPress={() => menu(m)} style={[styles.msgRow, m.is_mine && styles.mine]}>
              <View
                style={[
                  styles.bubble,
                  m.is_mine ? { backgroundColor: theme.primary } : { backgroundColor: theme.backgroundElement },
                ]}>
                <ThemedText style={m.is_mine ? { color: theme.onPrimary } : undefined}>{m.content}</ThemedText>
              </View>
              <ThemedText type="small" themeColor="textSecondary" style={styles.time}>
                {timeLabel(m.created_at)}
                {m.is_mine && m.read_at ? ' · 읽음' : ''}
              </ThemedText>
            </Pressable>
          )}
        />
        <SafeAreaView edges={['bottom']} style={[styles.composer, { borderColor: theme.border }]}>
          <ErrorText message={error} />
          {blocked ? (
            <ThemedText type="small" themeColor="textSecondary">
              {blocked}
            </ThemedText>
          ) : (
            <View style={styles.inputRow}>
              <TextInput
                value={text}
                onChangeText={setText}
                multiline
                maxLength={1000}
                placeholder="쪽지 쓰기"
                placeholderTextColor={theme.textSecondary}
                style={[styles.input, { color: theme.text, backgroundColor: theme.backgroundElement }]}
              />
              <Pressable
                accessibilityRole="button"
                onPress={send}
                disabled={sending || !text.trim()}
                style={[styles.send, { backgroundColor: theme.primary, opacity: sending || !text.trim() ? 0.5 : 1 }]}>
                <ThemedText type="smallBold" style={{ color: theme.onPrimary }}>
                  보내기
                </ThemedText>
              </Pressable>
            </View>
          )}
        </SafeAreaView>
      </KeyboardAvoidingView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  list: { padding: Spacing.three, gap: Spacing.two },
  empty: { textAlign: 'center', marginVertical: Spacing.five, transform: [{ scaleY: -1 }] },
  msgRow: { alignItems: 'flex-start', gap: 2 },
  mine: { alignItems: 'flex-end' },
  bubble: { maxWidth: '80%', borderRadius: 16, paddingHorizontal: Spacing.three, paddingVertical: Spacing.two },
  time: { fontSize: 11 },
  composer: { borderTopWidth: StyleSheet.hairlineWidth, paddingHorizontal: Spacing.three, paddingTop: Spacing.two, gap: Spacing.one },
  inputRow: { flexDirection: 'row', alignItems: 'flex-end', gap: Spacing.two, paddingBottom: Spacing.two },
  input: { flex: 1, minHeight: 40, maxHeight: 120, borderRadius: 20, paddingHorizontal: Spacing.three, paddingTop: 10, paddingBottom: 10, fontSize: 16 },
  send: { height: 40, borderRadius: 20, paddingHorizontal: Spacing.three, alignItems: 'center', justifyContent: 'center' },
});
