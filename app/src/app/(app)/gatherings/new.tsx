import { router, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Chips } from '@/components/chips';
import { Button, ErrorText, TextField } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, type Gathering } from '@/lib/api';
import { nextDays, parseTime } from '@/lib/when-input';

export default function NewGathering() {
  const params = useLocalSearchParams<{ kind?: string }>();
  const theme = useTheme();
  const days = useMemo(() => nextDays(), []);
  const [kind, setKind] = useState<Gathering['kind']>(params.kind === 'share' ? 'share' : 'walk');
  const [species, setSpecies] = useState<Gathering['species']>('all');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [place, setPlace] = useState('');
  const [day, setDay] = useState('0');
  const [time, setTime] = useState('19:00');
  const [capacity, setCapacity] = useState(kind === 'share' ? '1' : '3');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const hm = parseTime(time);
    if (!hm) return setError('시간을 19:00 처럼 입력해 주세요.');
    const date = days[Number(day)].date;
    const startsAt = new Date(date.getFullYear(), date.getMonth(), date.getDate(), hm[0], hm[1]);
    if (startsAt.getTime() < Date.now()) return setError('지난 시간이에요. 시간을 다시 골라 주세요.');

    setSaving(true);
    setError(null);
    try {
      const g = await api<Gathering>('/gatherings', {
        method: 'POST',
        body: {
          kind,
          species,
          title: title.trim(),
          content: content.trim(),
          place_name: place.trim(),
          starts_at: startsAt.toISOString(),
          capacity: Number(capacity) || 1,
        },
      });
      router.replace({ pathname: '/gatherings/[id]', params: { id: String(g.id) } });
    } catch (e) {
      setError(e instanceof Error ? e.message : '만들지 못했어요.');
    } finally {
      setSaving(false);
    }
  };

  const isShare = kind === 'share';

  return (
    <ThemedView style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Chips
          value={kind}
          onChange={(k) => {
            setKind(k);
            setCapacity(k === 'share' ? '1' : '3');
          }}
          options={[
            { value: 'walk', label: '산책 모임' },
            { value: 'share', label: '나눔' },
          ]}
        />
        <Chips
          value={species}
          onChange={setSpecies}
          options={[
            { value: 'all', label: '누구나' },
            { value: 'dog', label: '강아지' },
            { value: 'cat', label: '고양이' },
          ]}
        />
        <TextField
          label="제목"
          value={title}
          onChangeText={setTitle}
          maxLength={50}
          placeholder={isShare ? '예: 고양이 모래 2포 나눔해요' : '예: 저녁 한강 산책 같이 해요'}
        />
        <View style={styles.field}>
          <ThemedText type="smallBold">내용</ThemedText>
          <TextInput
            value={content}
            onChangeText={setContent}
            multiline
            maxLength={2000}
            textAlignVertical="top"
            placeholder={isShare ? '물건 상태, 건네는 방법을 적어 주세요' : '코스, 반려동물 크기·성격 조건 등을 적어 주세요'}
            placeholderTextColor={theme.textSecondary}
            style={[styles.textarea, { color: theme.text, borderColor: theme.border }]}
          />
        </View>
        <TextField
          label={isShare ? '건네는 곳' : '만나는 곳'}
          value={place}
          onChangeText={setPlace}
          maxLength={100}
          placeholder="예: 망원한강공원 2번 출입구"
        />
        <View style={styles.field}>
          <ThemedText type="smallBold">날짜</ThemedText>
          <Chips value={day} onChange={setDay} options={days} />
        </View>
        <View style={styles.row}>
          <View style={styles.half}>
            <TextField label="시간" value={time} onChangeText={setTime} placeholder="19:00" maxLength={5} keyboardType="numbers-and-punctuation" />
          </View>
          <View style={styles.half}>
            <TextField
              label={isShare ? '받을 사람 수' : '모집 인원 (나 제외)'}
              value={capacity}
              onChangeText={setCapacity}
              keyboardType="number-pad"
              maxLength={2}
            />
          </View>
        </View>
        <ThemedText type="small" themeColor="textSecondary">
          만난 자리에서 서로 QR을 찍으면 만남이 기록돼요. 만남이 쌓이면 이웃에게 부탁할 수 있어요.
        </ThemedText>
        <ErrorText message={error} />
        <Button
          title={isShare ? '나눔 올리기' : '모임 열기'}
          onPress={submit}
          loading={saving}
          disabled={!title.trim() || !place.trim()}
        />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.three },
  field: { gap: Spacing.one },
  textarea: { borderWidth: 1, borderRadius: 10, padding: Spacing.three, minHeight: 120, fontSize: 16 },
  row: { flexDirection: 'row', gap: Spacing.three },
  half: { flex: 1 },
});
