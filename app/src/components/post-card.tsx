import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { Post } from '@/lib/api';
import { SPECIES_LABEL, timeAgo } from '@/lib/format';

export function PostCard({ post }: { post: Post }) {
  const theme = useTheme();
  const thumb = post.images[0];
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push({ pathname: '/posts/[id]', params: { id: String(post.id) } })}
      style={({ pressed }) => [styles.card, { borderColor: theme.border, opacity: pressed ? 0.7 : 1 }]}>
      <View style={styles.body}>
        <ThemedText type="smallBold" numberOfLines={1}>
          {post.title}
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary" numberOfLines={2}>
          {post.content}
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary" style={styles.meta}>
          {[
            post.species !== 'all' ? SPECIES_LABEL[post.species] : null,
            post.region_name || null,
            timeAgo(post.created_at),
            post.like_count ? `♥ ${post.like_count}` : null,
            post.comment_count ? `댓글 ${post.comment_count}` : null,
          ]
            .filter(Boolean)
            .join(' · ')}
        </ThemedText>
      </View>
      {thumb && <Image source={{ uri: thumb.url }} style={styles.thumb} contentFit="cover" accessibilityIgnoresInvertColors />}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    gap: Spacing.three,
    paddingVertical: Spacing.three,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  body: { flex: 1, gap: 2 },
  meta: { fontSize: 12, marginTop: 2 },
  thumb: { width: 72, height: 72, borderRadius: 10 },
});
