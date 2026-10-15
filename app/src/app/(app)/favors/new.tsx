import { router, useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Chips } from '@/components/chips';
import { Agree, Button, ErrorText, TextField } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, type CareSheetDraft, type CareSheetInput, type Favor, type Page, type Pet } from '@/lib/api';
import { FAVOR_TERMS } from '@/lib/favor-terms';
import { SIZE_LABEL } from '@/lib/format';
import { combine, nextDays, parseTime } from '@/lib/when-input';

const DURATIONS = [
  { value: '30', label: '30분' },
  { value: '60', label: '1시간' },
  { value: '90', label: '1시간 30분' },
  { value: '120', label: '2시간' },
];

const numOrNull = (s: string) => (s.trim() === '' ? null : Number(s.replace(/\D/g, '')) || 0);
const str = (n: number | null) => (n === null ? '' : String(n));

export default function NewFavor() {
  const theme = useTheme();
  const days = useMemo(() => nextDays(), []);
  const [pets, setPets] = useState<Pet[] | null>(null);
  const [petId, setPetId] = useState('');
  const [kind, setKind] = useState<Favor['kind']>('walk');
  const [visitHome, setVisitHome] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [place, setPlace] = useState('');
  const [day, setDay] = useState('0');
  const [time, setTime] = useState('19:00');
  const [duration, setDuration] = useState('30');
  const [sheet, setSheet] = useState<CareSheetInput | null>(null);
  const [draft, setDraft] = useState<CareSheetDraft | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSheet = useCallback(async (id: string) => {
    setSheet(null);
    try {
      const d = await api<CareSheetDraft>(`/pets/${id}/care-sheet?days=14`);
      setDraft(d);
      setSheet({ meal: d.meal, meds: d.meds, condition: d.condition, walk: d.walk, notes: d.notes, caution: d.caution });
    } catch (e) {
      setError(e instanceof Error ? e.message : '돌봄 시트를 불러오지 못했어요.');
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      if (pets) return;
      api<Page<Pet>>('/pets')
        .then((page) => {
          const ok = page.results.filter((p) => p.verification_status === 'approved');
          setPets(ok);
          if (ok[0]) {
            setPetId(String(ok[0].id));
            loadSheet(String(ok[0].id));
          }
        })
        .catch((e) => setError(e instanceof Error ? e.message : '반려동물을 불러오지 못했어요.'));
    }, [pets, loadSheet]),
  );

  const patch = (p: Partial<CareSheetInput>) => setSheet((s) => (s ? { ...s, ...p } : s));

  const submit = async () => {
    if (!sheet) return;
    const hm = parseTime(time);
    if (!hm) return setError('시간을 19:00 처럼 입력해 주세요.');
    const startsAt = combine(days[Number(day)].date, hm);
    if (startsAt.getTime() < Date.now()) return setError('지난 시간이에요. 시간을 다시 골라 주세요.');

    setSaving(true);
    setError(null);
    try {
      const f = await api<Favor>('/favors', {
        method: 'POST',
        body: {
          pet_id: Number(petId),
          kind,
          visit_home: visitHome,
          title: title.trim(),
          content: content.trim(),
          place_name: place.trim(),
          starts_at: startsAt.toISOString(),
          duration_minutes: Number(duration),
          care_sheet_input: { ...sheet, meds: sheet.meds.filter((m) => m.name.trim()) },
          agree_terms: agreed,
        },
      });
      router.replace({ pathname: '/favors/[id]', params: { id: String(f.id) } });
    } catch (e) {
      setError(e instanceof Error ? e.message : '올리지 못했어요.');
    } finally {
      setSaving(false);
    }
  };

  if (pets && pets.length === 0) {
    return (
      <ThemedView style={[styles.flex, styles.container]}>
        <ThemedText>인증을 마친 반려동물이 있어야 부탁할 수 있어요. 마이 탭에서 반려동물을 인증해 주세요.</ThemedText>
      </ThemedView>
    );
  }

  const b = draft?.basic;
  const inputStyle = [styles.input, { color: theme.text, borderColor: theme.border }];

  return (
    <ThemedView style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <ThemedText type="small" themeColor="textSecondary">
          만남 인증을 한 이웃에게만 보여요. 지금은 2시간 이내의 짧은 부탁만 할 수 있어요.
        </ThemedText>

        {pets && pets.length > 1 && (
          <View style={styles.field}>
            <ThemedText type="smallBold">누구를 부탁할까요?</ThemedText>
            <Chips
              value={petId}
              onChange={(id) => {
                setPetId(id);
                loadSheet(id);
              }}
              options={pets.map((p) => ({ value: String(p.id), label: p.name }))}
            />
          </View>
        )}

        <View style={styles.field}>
          <ThemedText type="smallBold">어떤 부탁인가요?</ThemedText>
          <Chips
            value={kind}
            onChange={setKind}
            options={[
              { value: 'walk', label: '산책' },
              { value: 'meal', label: '밥 주기' },
              { value: 'hospital', label: '병원 동행' },
              { value: 'etc', label: '기타' },
            ]}
          />
          <Agree checked={visitHome} onChange={setVisitHome} label="우리 집에 들어와야 해요 (단골 이웃만 볼 수 있어요)" />
        </View>

        <TextField label="제목" value={title} onChangeText={setTitle} maxLength={50} placeholder="예: 저녁 산책 30분만 부탁해요" />
        <View style={styles.field}>
          <ThemedText type="smallBold">내용</ThemedText>
          <TextInput
            value={content}
            onChangeText={setContent}
            multiline
            maxLength={2000}
            textAlignVertical="top"
            placeholder="왜 부탁하는지, 건네는 방법 등을 적어 주세요"
            placeholderTextColor={theme.textSecondary}
            style={[inputStyle, styles.textarea]}
          />
        </View>
        {!visitHome ? (
          <TextField label="만나는 곳" value={place} onChangeText={setPlace} maxLength={100} placeholder="예: 망원동 OO아파트 정문" />
        ) : (
          <ThemedText type="small" themeColor="textSecondary">
            집 주소는 약속이 잡힌 뒤 맡은 이웃에게 직접 알려 주세요.
          </ThemedText>
        )}

        <View style={styles.field}>
          <ThemedText type="smallBold">날짜</ThemedText>
          <Chips value={day} onChange={setDay} options={days} />
        </View>
        <TextField label="시작 시간" value={time} onChangeText={setTime} placeholder="19:00" maxLength={5} keyboardType="numbers-and-punctuation" />
        <View style={styles.field}>
          <ThemedText type="smallBold">얼마나 걸리나요?</ThemedText>
          <Chips value={duration} onChange={setDuration} options={DURATIONS} />
        </View>

        {/* 돌봄 시트 */}
        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="smallBold">🗒 돌봄 시트</ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            약·식사 같은 자세한 내용은 맡은 이웃에게만 보여요. 다른 이웃에겐 산책 시간과 성격만 보여요.
            {draft && draft.source.from_journal.length === 0 ? ' 일기를 쓰면 다음부터 자동으로 채워져요.' : ''}
          </ThemedText>
          {!sheet ? (
            <ActivityIndicator />
          ) : (
            <>
              {b && (
                <ThemedText type="small">
                  {[b.name, b.breed, SIZE_LABEL[b.size as keyof typeof SIZE_LABEL] ?? '', b.age !== null ? `${b.age}살` : '', b.traits.join(', ')]
                    .filter(Boolean)
                    .join(' · ')}
                </ThemedText>
              )}
              <ThemedText type="smallBold">식사</ThemedText>
              <View style={styles.row}>
                <TextInput
                  value={str(sheet.meal.times_per_day)}
                  onChangeText={(v) => patch({ meal: { ...sheet.meal, times_per_day: numOrNull(v) } })}
                  placeholder="하루 몇 번"
                  keyboardType="number-pad"
                  maxLength={2}
                  placeholderTextColor={theme.textSecondary}
                  style={[inputStyle, styles.third]}
                />
                <TextInput
                  value={sheet.meal.amount}
                  onChangeText={(v) => patch({ meal: { ...sheet.meal, amount: v } })}
                  placeholder="1회 양"
                  maxLength={50}
                  placeholderTextColor={theme.textSecondary}
                  style={[inputStyle, styles.third]}
                />
                <TextInput
                  value={sheet.meal.food}
                  onChangeText={(v) => patch({ meal: { ...sheet.meal, food: v } })}
                  placeholder="사료"
                  maxLength={50}
                  placeholderTextColor={theme.textSecondary}
                  style={[inputStyle, styles.third]}
                />
              </View>

              <ThemedText type="smallBold">약</ThemedText>
              {sheet.meds.map((m, i) => (
                <View key={i} style={styles.row}>
                  {(['name', 'dose', 'time'] as const).map((k) => (
                    <TextInput
                      key={k}
                      value={m[k]}
                      onChangeText={(v) => patch({ meds: sheet.meds.map((x, j) => (j === i ? { ...x, [k]: v } : x)) })}
                      placeholder={{ name: '약 이름', dose: '용량', time: '시간' }[k]}
                      maxLength={50}
                      placeholderTextColor={theme.textSecondary}
                      style={[inputStyle, styles.third]}
                    />
                  ))}
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="약 지우기"
                    onPress={() => patch({ meds: sheet.meds.filter((_, j) => j !== i) })}
                    style={styles.remove}>
                    <ThemedText themeColor="textSecondary">✕</ThemedText>
                  </Pressable>
                </View>
              ))}
              {sheet.meds.length < 10 && (
                <ThemedText
                  type="linkPrimary"
                  accessibilityRole="button"
                  onPress={() => patch({ meds: [...sheet.meds, { name: '', dose: '', time: '' }] })}>
                  + 약 추가
                </ThemedText>
              )}

              <ThemedText type="smallBold">평소 산책</ThemedText>
              <View style={styles.row}>
                <TextInput
                  value={str(sheet.walk.minutes)}
                  onChangeText={(v) => patch({ walk: { ...sheet.walk, minutes: numOrNull(v) } })}
                  placeholder="한 번에 몇 분"
                  keyboardType="number-pad"
                  maxLength={3}
                  placeholderTextColor={theme.textSecondary}
                  style={[inputStyle, styles.half]}
                />
                <TextInput
                  value={str(sheet.walk.per_week)}
                  onChangeText={(v) => patch({ walk: { ...sheet.walk, per_week: numOrNull(v) } })}
                  placeholder="주 몇 번"
                  keyboardType="number-pad"
                  maxLength={2}
                  placeholderTextColor={theme.textSecondary}
                  style={[inputStyle, styles.half]}
                />
              </View>

              <TextField label="요즘 컨디션" value={sheet.condition} onChangeText={(v) => patch({ condition: v })} maxLength={200} placeholder="예: 잘 먹고 활발해요" />
              <TextField label="최근 특이사항" value={sheet.notes} onChangeText={(v) => patch({ notes: v })} maxLength={500} placeholder="예: 지난주 피부약 끝남" />
              <TextField label="주의할 점" value={sheet.caution} onChangeText={(v) => patch({ caution: v })} maxLength={500} placeholder="예: 자전거를 보면 짖어요, 다른 개와 인사 X" />
            </>
          )}
        </ThemedView>

        {/* 책임 범위 동의 */}
        <View style={styles.field}>
          <ThemedText type="smallBold">부탁 약속</ThemedText>
          {FAVOR_TERMS.map((t) => (
            <ThemedText key={t} type="small" themeColor="textSecondary">
              · {t}
            </ThemedText>
          ))}
          <Agree checked={agreed} onChange={setAgreed} label="위 내용을 확인했고 동의해요" />
        </View>

        <ErrorText message={error} />
        <Button
          title="부탁 올리기"
          onPress={submit}
          loading={saving}
          disabled={!sheet || !agreed || !title.trim() || (!visitHome && !place.trim())}
        />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.three, paddingBottom: Spacing.six },
  field: { gap: Spacing.one },
  card: { borderRadius: 12, padding: Spacing.three, gap: Spacing.two },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: Spacing.two, paddingVertical: 10, fontSize: 15 },
  textarea: { minHeight: 100, padding: Spacing.three },
  row: { flexDirection: 'row', gap: Spacing.two, alignItems: 'center' },
  third: { flex: 1, minWidth: 0 },
  half: { flex: 1, minWidth: 0 },
  remove: { paddingHorizontal: Spacing.one },
});
