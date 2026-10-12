import { Image } from 'expo-image';
import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';
import { useTheme } from '@/hooks/use-theme';
import { api, type Comment, type Post } from '@/lib/api';
import { SPECIES_LABEL, timeAgo } from '@/lib/format';
import { askReport } from '@/lib/report';

export default function PostDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const theme = useTheme();
  const { me } = useSession();
  const canWrite = !!me?.is_verified_member;
  const [post, setPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([api<Post>(`/posts/${id}`), api<Comment[]>(`/posts/${id}/comments`)]);
      setPost(p);
      setComments(c);
    } catch (e) {
      setError(e instanceof Error ? e.message : '글을 불러오지 못했어요.');
    }
  }, [id]);

  // 수정 화면에서 돌아올 때도 다시 불러온다
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const toggleLike = async () => {
    if (!post) return;
    try {
      setPost(await api<Post>(`/posts/${post.id}/like`, { method: post.is_liked ? 'DELETE' : 'POST' }));
    } catch (e) {
      setError(e instanceof Error ? e.message : null);
    }
  };

  const sendComment = async () => {
    if (!draft.trim()) return;
    setSending(true);
    try {
      const c = await api<Comment>(`/posts/${id}/comments`, { method: 'POST', body: { content: draft.trim() } });
      setComments((prev) => [...prev, c]);
      setDraft('');
      setPost((p) => (p ? { ...p, comment_count: p.comment_count + 1 } : p));
    } catch (e) {
      setError(e instanceof Error ? e.message : '댓글을 남기지 못했어요.');
    } finally {
      setSending(false);
    }
  };

  const openMenu = () => {
    if (!post) return;
    if (post.is_mine) {
      Alert.alert('내 글', undefined, [
        { text: '수정', onPress: () => router.push({ pathname: '/posts/new', params: { edit: String(post.id) } }) },
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            await api(`/posts/${post.id}`, { method: 'DELETE' });
            router.back();
          },
        },
        { text: '취소', style: 'cancel' },
      ]);
    } else if (canWrite) {
      askReport(`/posts/${post.id}/report`, (hidden) => hidden && router.back());
    }
  };

  const onCommentLongPress = (c: Comment) => {
    if (c.is_mine) {
      Alert.alert('댓글 삭제', '이 댓글을 삭제할까요?', [
        { text: '취소', style: 'cancel' },
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            await api(`/comments/${c.id}`, { method: 'DELETE' });
            setComments((prev) => prev.filter((x) => x.id !== c.id));
          },
        },
      ]);
    } else if (canWrite) {
      askReport(`/comments/${c.id}/report`, (hidden) => hidden && setComments((prev) => prev.filter((x) => x.id !== c.id)));
    }
  };

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen
        options={{
          title: '',
          headerRight: () =>
            post && (post.is_mine || canWrite) ? (
              <ThemedText type="linkPrimary" onPress={openMenu} accessibilityRole="button" style={styles.headerAction}>
                {post.is_mine ? '관리' : '신고'}
              </ThemedText>
            ) : null,
        }}
      />
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
        <ScrollView contentContainerStyle={styles.container}>
          <ErrorText message={error} />
          {post && (
            <>
              {post.is_hidden && (
                <ThemedView type="backgroundElement" style={styles.notice}>
                  <ThemedText type="small">신고가 누적되어 다른 사람에게 보이지 않는 글이에요. 운영자가 확인 중이에요.</ThemedText>
                </ThemedView>
              )}
              <View style={styles.section}>
                <ThemedText type="small" themeColor="textSecondary">
                  {[post.author.nickname, post.region_name || null, timeAgo(post.created_at)].filter(Boolean).join(' · ')}
                </ThemedText>
                <ThemedText style={styles.postTitle}>{post.title}</ThemedText>
                <ThemedText>{post.content}</ThemedText>
              </View>

              {post.images.map((img) => (
                <Image
                  key={img.id}
                  source={{ uri: img.url }}
                  style={[styles.image, { aspectRatio: img.width / img.height }]}
                  contentFit="cover"
                />
              ))}

              <View style={styles.tagRow}>
                {post.species !== 'all' && <Tag label={SPECIES_LABEL[post.species]} />}
                {post.tags.map((t) => (
                  <Tag key={t} label={`#${t}`} />
                ))}
              </View>

              <Pressable
                accessibilityRole="button"
                disabled={!canWrite}
                onPress={toggleLike}
                style={[styles.likeButton, { borderColor: post.is_liked ? theme.primary : theme.border }]}>
                <ThemedText type="smallBold" style={{ color: post.is_liked ? theme.primary : theme.text }}>
                  {post.is_liked ? '♥' : '♡'} 좋아요 {post.like_count}
                </ThemedText>
              </Pressable>

              <View style={[styles.section, styles.comments, { borderTopColor: theme.border }]}>
                <ThemedText type="smallBold">댓글 {post.comment_count}</ThemedText>
                {comments.map((c) => (
                  <Pressable key={c.id} onLongPress={() => onCommentLongPress(c)} style={styles.comment}>
                    <ThemedText type="small" themeColor="textSecondary">
                      {c.author.nickname} · {timeAgo(c.created_at)}
                      {c.is_hidden ? ' · 숨김' : ''}
                    </ThemedText>
                    <ThemedText type="small">{c.content}</ThemedText>
                  </Pressable>
                ))}
                {comments.length > 0 && canWrite && (
                  <ThemedText type="small" themeColor="textSecondary" style={styles.hint}>
                    댓글을 길게 누르면 삭제하거나 신고할 수 있어요.
                  </ThemedText>
                )}
              </View>
            </>
          )}
        </ScrollView>

        {canWrite ? (
          <View style={[styles.inputBar, { borderTopColor: theme.border, backgroundColor: theme.background }]}>
            <TextInput
              value={draft}
              onChangeText={setDraft}
              placeholder="댓글을 남겨 보세요"
              placeholderTextColor={theme.textSecondary}
              maxLength={500}
              multiline
              style={[styles.input, { backgroundColor: theme.backgroundElement, color: theme.text }]}
            />
            <ThemedText
              type="smallBold"
              accessibilityRole="button"
              onPress={sending ? undefined : sendComment}
              style={{ color: draft.trim() ? theme.primary : theme.textSecondary }}>
              등록
            </ThemedText>
          </View>
        ) : (
          <ThemedText type="small" themeColor="textSecondary" style={styles.readonly}>
            인증을 마치면 댓글과 좋아요를 남길 수 있어요.
          </ThemedText>
        )}
      </KeyboardAvoidingView>
    </ThemedView>
  );
}

function Tag({ label }: { label: string }) {
  return (
    <ThemedView type="backgroundElement" style={styles.tag}>
      <ThemedText type="small">{label}</ThemedText>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.three, paddingBottom: Spacing.five },
  section: { gap: Spacing.two },
  postTitle: { fontSize: 20, lineHeight: 28, fontWeight: 700 },
  notice: { padding: Spacing.three, borderRadius: 10 },
  image: { width: '100%', borderRadius: 12 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  tag: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 },
  likeButton: { alignSelf: 'flex-start', borderWidth: 1, borderRadius: 999, paddingHorizontal: Spacing.three, paddingVertical: 6 },
  comments: { borderTopWidth: StyleSheet.hairlineWidth, paddingTop: Spacing.three },
  comment: { gap: 2, paddingVertical: Spacing.two },
  hint: { fontSize: 12 },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  input: { flex: 1, borderRadius: 18, paddingHorizontal: Spacing.three, paddingVertical: 8, maxHeight: 100, fontSize: 15 },
  headerAction: { paddingHorizontal: Spacing.three },
  readonly: { textAlign: 'center', padding: Spacing.three },
});
