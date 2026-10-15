import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Chips } from '@/components/chips';
import { Button, ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, uploadImage, type Page, type Pet } from '@/lib/api';
import { getCurrentCoords } from '@/lib/location';

const MAX_PHOTOS = 3;
type Tri = 'yes' | 'no' | '';

function pastDays(n = 7) {
  const today = new Date();
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i);
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    return { value: iso, label: i === 0 ? '오늘' : i === 1 ? '어제' : `${d.getMonth() + 1}/${d.getDate()}` };
  });
}

const triToBool = (v: Tri) => (v === '' ? null : v === 'yes');

function Question({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.q}>
      <ThemedText type="smallBold">{title}</ThemedText>
      {children}
    </View>
  );
}

/** 30초 후기: 동반 조건 체크 위주 */
export default function PlaceReviewForm() {
  const { place, name } = useLocalSearchParams<{ place: string; name?: string }>();
  const theme = useTheme();
  const days = useMemo(() => pastDays(), []);
  const [pets, setPets] = useState<Pet[] | null>(null);
  const [petId, setPetId] = useState('');
  const [visitedOn, setVisitedOn] = useState(days[0].value);
  const [admitted, setAdmitted] = useState<Tri>('');
  const [space, setSpace] = useState<'' | 'indoor' | 'outdoor' | 'separate'>('');
  const [floor, setFloor] = useState<Tri>('');
  const [fee, setFee] = useState<Tri>('');
  const [comment, setComment] = useState('');
  const [photos, setPhotos] = useState<ImagePicker.ImagePickerAsset[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      if (pets) return;
      api<Page<Pet>>('/pets')
        .then((page) => {
          const ok = page.results.filter((p) => p.verification_status === 'approved');
          setPets(ok);
          if (ok[0]) setPetId(String(ok[0].id));
        })
        .catch((e) => setError(e instanceof Error ? e.message : '반려동물을 불러오지 못했어요.'));
    }, [pets]),
  );

  const pick = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsMultipleSelection: true,
      selectionLimit: MAX_PHOTOS - photos.length,
      quality: 0.8,
      preferredAssetRepresentationMode: ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Compatible,
    });
    if (!result.canceled) setPhotos((cur) => [...cur, ...result.assets].slice(0, MAX_PHOTOS));
  };

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      // 장소 근처에서 쓰면 '방문 확인'. 위치는 확인에만 쓰고 저장하지 않는다.
      const coords = await getCurrentCoords().catch(() => null);
      const imageIds = [];
      for (const p of photos) imageIds.push((await uploadImage(p)).id);
      await api(`/places/${place}/reviews`, {
        method: 'POST',
        body: {
          pet_id: Number(petId),
          visited_on: visitedOn,
          admitted: admitted === 'yes',
          space,
          floor_ok: triToBool(floor),
          extra_fee: triToBool(fee),
          comment: comment.trim(),
          image_ids: imageIds,
          ...(coords ? { lat: coords.lat, lng: coords.lng } : {}),
        },
      });
      router.back();
    } catch (e) {
      setError(e instanceof Error ? e.message : '남기지 못했어요.');
    } finally {
      setSaving(false);
    }
  };

  const pet = pets?.find((p) => String(p.id) === petId);
  const triOptions = (yes: string, no: string) => [
    { value: 'yes' as const, label: yes },
    { value: 'no' as const, label: no },
    { value: '' as const, label: '모르겠어요' },
  ];

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen options={{ title: name ? `${name} 후기` : '30초 후기' }} />
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {pets && pets.length === 0 && <ThemedText>인증을 마친 반려동물이 있어야 후기를 남길 수 있어요.</ThemedText>}

        <Question title="누구와 다녀왔나요?">
          {pets && pets.length > 1 && (
            <Chips value={petId} onChange={setPetId} options={pets.map((p) => ({ value: String(p.id), label: p.name }))} />
          )}
          {pet && (
            <ThemedText type="small" themeColor="textSecondary">
              {pet.name}의 크기·체중이 후기에 함께 표시돼요{pet.weight_kg ? ` (${Number(pet.weight_kg)}kg)` : ''}.
              {!pet.size || !pet.weight_kg ? ' 마이 탭에서 크기·체중을 넣어 두면 더 도움이 돼요.' : ''}
            </ThemedText>
          )}
        </Question>

        <Question title="언제 갔나요?">
          <Chips value={visitedOn} onChange={setVisitedOn} options={days} />
        </Question>

        <Question title="함께 들어갈 수 있었나요?">
          <Chips
            value={admitted}
            onChange={setAdmitted}
            options={[
              { value: 'yes', label: '네, 같이 들어갔어요' },
              { value: 'no', label: '아니요' },
            ]}
          />
        </Question>

        {admitted === 'yes' && (
          <>
            <Question title="어디까지 함께 있었나요?">
              <Chips
                value={space}
                onChange={setSpace}
                options={[
                  { value: 'indoor', label: '실내' },
                  { value: 'outdoor', label: '테라스·야외만' },
                  { value: 'separate', label: '전용 공간' },
                  { value: '', label: '모르겠어요' },
                ]}
              />
            </Question>
            <Question title="바닥에 내려놔도 됐나요?">
              <Chips value={floor} onChange={setFloor} options={triOptions('네', '안기·켄넬 필요')} />
            </Question>
          </>
        )}

        <Question title="반려동물 추가 요금이 있었나요?">
          <Chips value={fee} onChange={setFee} options={triOptions('있어요', '없어요')} />
        </Question>

        <Question title="한 줄 남기기 (선택)">
          <TextInput
            value={comment}
            onChangeText={setComment}
            maxLength={300}
            multiline
            placeholder="예: 테라스 자리 4개뿐이라 주말엔 일찍 가세요"
            placeholderTextColor={theme.textSecondary}
            style={[styles.input, { color: theme.text, borderColor: theme.border }]}
          />
        </Question>

        <Question title="사진 (선택)">
          <ThemedText type="small" themeColor="textSecondary">
            입구 안내문·메뉴판처럼 동반 조건이 보이는 사진이면 좋아요.
          </ThemedText>
          <View style={styles.photos}>
            {photos.map((p, i) => (
              <Pressable key={p.uri} onPress={() => setPhotos((cur) => cur.filter((_, j) => j !== i))} accessibilityLabel="사진 빼기">
                <Image source={{ uri: p.uri }} style={styles.photo} contentFit="cover" />
              </Pressable>
            ))}
            {photos.length < MAX_PHOTOS && (
              <Pressable onPress={pick} style={[styles.photo, styles.add, { borderColor: theme.border }]} accessibilityRole="button" accessibilityLabel="사진 추가">
                <ThemedText themeColor="textSecondary">＋</ThemedText>
              </Pressable>
            )}
          </View>
        </Question>

        <ThemedText type="small" themeColor="textSecondary">
          장소 근처에서 남기면 &apos;방문 확인&apos;이 붙어요. 위치는 확인에만 쓰고 저장하지 않아요.
        </ThemedText>
        <ErrorText message={error} />
        <Button title="후기 남기기" onPress={submit} loading={saving} disabled={!petId || !admitted} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.four, paddingBottom: Spacing.six },
  q: { gap: Spacing.two },
  input: { borderWidth: 1, borderRadius: 10, padding: Spacing.three, minHeight: 72, fontSize: 16 },
  photos: { flexDirection: 'row', gap: Spacing.two },
  photo: { width: 72, height: 72, borderRadius: 8 },
  add: { borderWidth: 1, borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center' },
});
