import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Chips } from '@/components/chips';
import { Button, ErrorText, TextField } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, uploadImage, type ImageInfo, type Post } from '@/lib/api';

const MAX_IMAGES = 5;

type Photo = { kind: 'remote'; info: ImageInfo } | { kind: 'local'; asset: ImagePicker.ImagePickerAsset };

function parseTags(raw: string) {
  return Array.from(new Set(raw.split(/[\s,]+/).map((t) => t.replace(/^#/, '').trim()).filter(Boolean))).slice(0, 5);
}

export default function NewPost() {
  const { edit } = useLocalSearchParams<{ edit?: string }>();
  const theme = useTheme();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [species, setSpecies] = useState<Post['species']>('all');
  const [tags, setTags] = useState('');
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!edit) return;
    api<Post>(`/posts/${edit}`)
      .then((p) => {
        setTitle(p.title);
        setContent(p.content);
        setSpecies(p.species);
        setTags(p.tags.map((t) => `#${t}`).join(' '));
        setPhotos(p.images.map((info) => ({ kind: 'remote', info })));
      })
      .catch((e) => setError(e instanceof Error ? e.message : '글을 불러오지 못했어요.'));
  }, [edit]);

  const pickPhotos = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsMultipleSelection: true,
      selectionLimit: MAX_IMAGES - photos.length,
      quality: 0.8,
    });
    if (result.canceled) return;
    setPhotos((prev) =>
      [...prev, ...result.assets.map((asset) => ({ kind: 'local', asset }) as Photo)].slice(0, MAX_IMAGES),
    );
  };

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      // 새로 고른 사진만 업로드하고, 기존 사진과 순서대로 합친다
      const imageIds: number[] = [];
      for (const p of photos) {
        imageIds.push(p.kind === 'remote' ? p.info.id : (await uploadImage(p.asset)).id);
      }
      const body = { title: title.trim(), content: content.trim(), species, tags: parseTags(tags), image_ids: imageIds };
      const post = await api<Post>(edit ? `/posts/${edit}` : '/posts', { method: edit ? 'PATCH' : 'POST', body });
      if (edit) router.back();
      else router.replace({ pathname: '/posts/[id]', params: { id: String(post.id) } });
    } catch (e) {
      setError(e instanceof Error ? e.message : '저장하지 못했어요.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen options={{ title: edit ? '글 수정' : '글쓰기' }} />
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Chips
          value={species}
          onChange={setSpecies}
          options={[
            { value: 'all', label: '모두' },
            { value: 'dog', label: '강아지' },
            { value: 'cat', label: '고양이' },
          ]}
        />
        <TextField label="제목" value={title} onChangeText={setTitle} maxLength={50} />
        <View style={styles.field}>
          <ThemedText type="smallBold">내용</ThemedText>
          <TextInput
            value={content}
            onChangeText={setContent}
            multiline
            maxLength={3000}
            textAlignVertical="top"
            placeholder="동네 이웃과 나누고 싶은 이야기를 적어 주세요"
            placeholderTextColor={theme.textSecondary}
            style={[styles.textarea, { color: theme.text, borderColor: theme.border }]}
          />
        </View>
        <TextField label="태그 (최대 5개)" value={tags} onChangeText={setTags} placeholder="#산책 #대형견" autoCapitalize="none" />

        <View style={styles.field}>
          <ThemedText type="smallBold">
            사진 {photos.length}/{MAX_IMAGES}
          </ThemedText>
          <ScrollView horizontal contentContainerStyle={styles.photoRow}>
            {photos.length < MAX_IMAGES && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="사진 추가"
                onPress={pickPhotos}
                style={[styles.photo, styles.addPhoto, { borderColor: theme.border }]}>
                <ThemedText type="subtitle" themeColor="textSecondary">
                  +
                </ThemedText>
              </Pressable>
            )}
            {photos.map((p, i) => (
              <Pressable
                key={p.kind === 'remote' ? `r${p.info.id}` : `l${p.asset.uri}`}
                accessibilityLabel="사진 빼기"
                onPress={() => setPhotos((prev) => prev.filter((_, j) => j !== i))}>
                <Image source={{ uri: p.kind === 'remote' ? p.info.url : p.asset.uri }} style={styles.photo} contentFit="cover" />
                <ThemedText type="smallBold" style={styles.remove}>
                  ✕
                </ThemedText>
              </Pressable>
            ))}
          </ScrollView>
          <ThemedText type="small" themeColor="textSecondary">
            사진 속 위치 정보는 서버에서 지워져요.
          </ThemedText>
        </View>

        <ErrorText message={error} />
        <Button title={edit ? '수정하기' : '올리기'} onPress={submit} loading={saving} disabled={!title.trim() || !content.trim()} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.three },
  field: { gap: Spacing.one },
  textarea: { borderWidth: 1, borderRadius: 10, padding: Spacing.three, minHeight: 160, fontSize: 16 },
  photoRow: { gap: Spacing.two, paddingVertical: Spacing.one },
  photo: { width: 80, height: 80, borderRadius: 10 },
  addPhoto: { borderWidth: 1, borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center' },
  remove: {
    position: 'absolute',
    top: 4,
    right: 6,
    color: '#fff',
    textShadowColor: 'rgba(0,0,0,0.6)',
    textShadowRadius: 3,
  },
});
