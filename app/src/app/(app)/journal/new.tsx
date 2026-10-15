import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Chips } from '@/components/chips';
import { Agree, Button, ErrorText, TextField } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, uploadImage, type JournalEntry } from '@/lib/api';
import { isoDate, VITALITY_LABEL } from '@/lib/format';

const MAX_PHOTOS = 5;
type Med = { name: string; dose: string; time: string };

function recentDays(selected?: string) {
  const today = new Date();
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i);
    return { value: isoDate(d), label: i === 0 ? '오늘' : i === 1 ? '어제' : `${d.getMonth() + 1}/${d.getDate()}` };
  });
  if (selected && !days.some((d) => d.value === selected)) {
    days.push({ value: selected, label: `${Number(selected.slice(5, 7))}/${Number(selected.slice(8))}` });
  }
  return days;
}

const num = (s: string) => (s.trim() === '' ? null : Number(s.replace(/[^\d.]/g, '')) || null);

/** 건강 기록 / 일반 일기 */
export default function NewJournal() {
  const params = useLocalSearchParams<{ pet: string; kind: 'health' | 'daily'; date?: string }>();
  const kind = params.kind === 'health' ? 'health' : 'daily';
  const theme = useTheme();
  const days = useMemo(() => recentDays(params.date), [params.date]);
  const [date, setDate] = useState(params.date && params.date <= isoDate(new Date()) ? params.date : days[0].value);
  // 건강
  const [meals, setMeals] = useState('');
  const [amount, setAmount] = useState('');
  const [food, setFood] = useState('');
  const [vitality, setVitality] = useState('');
  const [medsMode, setMedsMode] = useState<'skip' | 'none' | 'some'>('skip');
  const [meds, setMeds] = useState<Med[]>([{ name: '', dose: '', time: '' }]);
  const [weight, setWeight] = useState('');
  // 공통
  const [content, setContent] = useState('');
  const [share, setShare] = useState(false);
  const [photos, setPhotos] = useState<ImagePicker.ImagePickerAsset[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      const imageIds = [];
      for (const p of photos) imageIds.push((await uploadImage(p)).id);
      const body: Record<string, unknown> = {
        pet_id: Number(params.pet),
        kind,
        date,
        content: content.trim(),
        share_in_care_sheet: share && !!content.trim(),
        image_ids: imageIds,
      };
      if (kind === 'health') {
        Object.assign(body, {
          meals_per_day: num(meals),
          meal_amount: amount.trim(),
          food: food.trim(),
          vitality: vitality ? Number(vitality) : null,
          meds: medsMode === 'skip' ? null : medsMode === 'none' ? [] : meds.filter((m) => m.name.trim()),
          weight_kg: num(weight),
        });
      }
      const e = await api<JournalEntry>('/journal', { method: 'POST', body });
      router.replace({ pathname: '/journal/[id]', params: { id: String(e.id) } });
    } catch (e) {
      setError(e instanceof Error ? e.message : '저장하지 못했어요.');
    } finally {
      setSaving(false);
    }
  };

  const inputStyle = [styles.input, { color: theme.text, borderColor: theme.border }];

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen options={{ title: kind === 'health' ? '건강 기록' : '일기 쓰기' }} />
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.field}>
          <ThemedText type="smallBold">날짜</ThemedText>
          <Chips value={date} onChange={setDate} options={days} />
        </View>

        {kind === 'health' && (
          <>
            <View style={styles.field}>
              <ThemedText type="smallBold">오늘 컨디션</ThemedText>
              <Chips
                value={vitality}
                onChange={setVitality}
                options={[1, 2, 3, 4, 5].map((v) => ({ value: String(v), label: `${v} ${VITALITY_LABEL[v]}` }))}
              />
            </View>

            <View style={styles.field}>
              <ThemedText type="smallBold">식사</ThemedText>
              <View style={styles.row}>
                <TextInput value={meals} onChangeText={setMeals} placeholder="하루 몇 번" keyboardType="number-pad" maxLength={2} placeholderTextColor={theme.textSecondary} style={[inputStyle, styles.cell]} />
                <TextInput value={amount} onChangeText={setAmount} placeholder="1회 양" maxLength={50} placeholderTextColor={theme.textSecondary} style={[inputStyle, styles.cell]} />
                <TextInput value={food} onChangeText={setFood} placeholder="사료" maxLength={50} placeholderTextColor={theme.textSecondary} style={[inputStyle, styles.cell]} />
              </View>
            </View>

            <View style={styles.field}>
              <ThemedText type="smallBold">약</ThemedText>
              <Chips
                value={medsMode}
                onChange={setMedsMode}
                options={[
                  { value: 'skip', label: '기록 안 함' },
                  { value: 'none', label: '먹는 약 없음' },
                  { value: 'some', label: '먹고 있어요' },
                ]}
              />
              {medsMode === 'some' && (
                <>
                  {meds.map((m, i) => (
                    <View key={i} style={styles.row}>
                      {(['name', 'dose', 'time'] as const).map((k) => (
                        <TextInput
                          key={k}
                          value={m[k]}
                          onChangeText={(v) => setMeds((cur) => cur.map((x, j) => (j === i ? { ...x, [k]: v } : x)))}
                          placeholder={{ name: '약 이름', dose: '용량', time: '시간' }[k]}
                          maxLength={50}
                          placeholderTextColor={theme.textSecondary}
                          style={[inputStyle, styles.cell]}
                        />
                      ))}
                    </View>
                  ))}
                  {meds.length < 10 && (
                    <ThemedText type="linkPrimary" onPress={() => setMeds((cur) => [...cur, { name: '', dose: '', time: '' }])}>
                      + 약 추가
                    </ThemedText>
                  )}
                </>
              )}
            </View>

            <TextField label="체중 (kg, 선택)" value={weight} onChangeText={setWeight} keyboardType="decimal-pad" maxLength={5} />
          </>
        )}

        <View style={styles.field}>
          <ThemedText type="smallBold">{kind === 'health' ? '메모 (선택)' : '내용'}</ThemedText>
          <TextInput
            value={content}
            onChangeText={setContent}
            multiline
            maxLength={3000}
            textAlignVertical="top"
            placeholder={kind === 'health' ? '예: 왼쪽 앞발을 자꾸 핥아요' : '오늘 있었던 일을 남겨 보세요'}
            placeholderTextColor={theme.textSecondary}
            style={[inputStyle, styles.textarea]}
          />
          {!!content.trim() && <Agree checked={share} onChange={setShare} label="부탁할 때 돌봄 시트 '최근 특이사항'에 넣기" />}
        </View>

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

        <ErrorText message={error} />
        <Button title="저장" onPress={submit} loading={saving} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.four, paddingBottom: Spacing.six },
  field: { gap: Spacing.two },
  row: { flexDirection: 'row', gap: Spacing.two },
  cell: { flex: 1, minWidth: 0 },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: Spacing.two, paddingVertical: 10, fontSize: 15 },
  textarea: { minHeight: 110, padding: Spacing.three },
  photos: { flexDirection: 'row', gap: Spacing.two, flexWrap: 'wrap' },
  photo: { width: 72, height: 72, borderRadius: 8 },
  add: { borderWidth: 1, borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center' },
});
