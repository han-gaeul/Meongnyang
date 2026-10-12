import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { CareSheetView } from '@/components/care-sheet-view';
import { Agree, Button, ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';
import { useTheme } from '@/hooks/use-theme';
import { api, type Favor, type FavorApplication } from '@/lib/api';
import { FAVOR_TERMS } from '@/lib/favor-terms';
import { FAVOR_KIND_LABEL, FAVOR_STATUS_LABEL, minutesLabel, SIZE_LABEL, whenLabel } from '@/lib/format';
import { askReport } from '@/lib/report';

export default function FavorDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const theme = useTheme();
  const { me } = useSession();
  const canWrite = !!me?.is_verified_member;
  const [f, setF] = useState<Favor | null>(null);
  const [apps, setApps] = useState<FavorApplication[]>([]);
  const [message, setMessage] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [thanks, setThanks] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadedAt, setLoadedAt] = useState(0);

  const load = useCallback(async () => {
    try {
      const data = await api<Favor>(`/favors/${id}`);
      setF(data);
      setLoadedAt(Date.now());
      if (data.is_requester) setApps(await api<FavorApplication[]>(`/favors/${id}/applications`));
    } catch (e) {
      setError(e instanceof Error ? e.message : '부탁을 불러오지 못했어요.');
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : '처리하지 못했어요.');
    } finally {
      setBusy(false);
    }
  };

  const confirm = (title: string, body: string, ok: string, fn: () => Promise<unknown>, destructive = false) =>
    Alert.alert(title, body, [
      { text: '아니요', style: 'cancel' },
      { text: ok, style: destructive ? 'destructive' : 'default', onPress: () => run(fn) },
    ]);

  const openMenu = () => {
    if (!f) return;
    if (f.is_requester) {
      if (f.status === 'done') return;
      confirm('부탁 취소', '이 부탁을 취소할까요?', '취소하기', async () => {
        await api(`/favors/${id}`, { method: 'DELETE' });
        router.back();
      }, true);
    } else {
      askReport(`/favors/${id}/report`, (hidden) => hidden && router.back());
    }
  };

  if (!f) {
    return (
      <ThemedView style={[styles.flex, styles.container]}>
        <ErrorText message={error} />
      </ThemedView>
    );
  }

  const s = f.care_summary;
  const mine = f.my_application;
  const pending = apps.filter((a) => a.status === 'pending');
  const started = new Date(f.starts_at).getTime() <= loadedAt;
  const iAmHelper = f.helper?.id === me?.id;

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen
        options={{
          title: FAVOR_KIND_LABEL[f.kind],
          headerRight: () =>
            (f.is_requester && f.status !== 'done' && f.status !== 'cancelled') || (!f.is_requester && canWrite) ? (
              <ThemedText type="linkPrimary" onPress={openMenu} accessibilityRole="button" style={styles.headerAction}>
                {f.is_requester ? '취소' : '신고'}
              </ThemedText>
            ) : null,
        }}
      />
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <ErrorText message={error} />

        <View style={styles.section}>
          <ThemedText type="smallBold" style={{ color: f.status === 'open' ? theme.primary : theme.textSecondary }}>
            {FAVOR_STATUS_LABEL[f.status]}
            {f.visit_home ? ' · 집 방문' : ''}
          </ThemedText>
          <ThemedText style={styles.title}>{f.title}</ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            {[f.requester.nickname, f.region_name || null].filter(Boolean).join(' · ')}
          </ThemedText>
        </View>

        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="smallBold">
            🕖 {whenLabel(f.starts_at)} · {minutesLabel(f.duration_minutes)}
          </ThemedText>
          {!!f.place_name && <ThemedText type="smallBold">📍 {f.place_name}</ThemedText>}
          <ThemedText type="small">
            🐾 {[f.pet.name, s.breed, SIZE_LABEL[s.size as keyof typeof SIZE_LABEL] ?? '', s.age !== null ? `${s.age}살` : '']
              .filter(Boolean)
              .join(' · ')}
          </ThemedText>
          {s.traits.length > 0 && <ThemedText type="small">성격: {s.traits.join(', ')}</ThemedText>}
          {s.walk.minutes !== null && <ThemedText type="small">평소 산책: 한 번에 {s.walk.minutes}분</ThemedText>}
        </ThemedView>

        {!!f.content && <ThemedText>{f.content}</ThemedText>}

        {f.care_sheet ? (
          <CareSheetView sheet={f.care_sheet} />
        ) : (
          <ThemedText type="small" themeColor="textSecondary">
            약·식사 같은 자세한 돌봄 시트는 부탁을 맡게 되면 보여요.
          </ThemedText>
        )}

        {f.helper && !iAmHelper && (
          <ThemedView type="backgroundElement" style={styles.card}>
            <ThemedText type="smallBold">
              {f.is_requester ? `🤝 ${f.helper.nickname}님이 맡아 주세요` : '다른 이웃이 맡았어요'}
            </ThemedText>
            {f.is_requester && f.status === 'matched' && (
              <ThemedText type="small" themeColor="textSecondary">
                {f.visit_home ? '집 주소와 출입 방법을 맡은 이웃에게 따로 알려 주세요. ' : ''}끝나면 아래 &apos;잘 마쳤어요&apos;를 눌러 주세요.
              </ThemedText>
            )}
          </ThemedView>
        )}

        {/* 부탁한 사람: 신청 관리 */}
        {f.is_requester && f.status === 'open' && (
          <View style={styles.section}>
            <ThemedText type="smallBold">맡겠다는 이웃 {pending.length}</ThemedText>
            {pending.length === 0 && (
              <ThemedText type="small" themeColor="textSecondary">
                아직 신청이 없어요. 만남 인증을 한 이웃에게만 보여요.
              </ThemedText>
            )}
            {pending.map((a) => (
              <ThemedView key={a.id} type="backgroundElement" style={styles.card}>
                <ThemedText type="smallBold">{a.user.nickname}</ThemedText>
                {!!a.message && <ThemedText type="small">“{a.message}”</ThemedText>}
                <View style={styles.row}>
                  <View style={styles.half}>
                    <Button
                      title="다음에요"
                      variant="secondary"
                      disabled={busy}
                      onPress={() => run(() => api(`/favors/${id}/applications/${a.id}/reject`, { method: 'POST' }))}
                    />
                  </View>
                  <View style={styles.half}>
                    <Button
                      title="부탁할게요"
                      disabled={busy}
                      onPress={() =>
                        confirm(
                          `${a.user.nickname}님에게 부탁할까요?`,
                          '약속이 잡히면 이 이웃에게 돌봄 시트 전체가 보여요.',
                          '부탁하기',
                          () => api(`/favors/${id}/applications/${a.id}/accept`, { method: 'POST' }),
                        )
                      }
                    />
                  </View>
                </View>
              </ThemedView>
            ))}
          </View>
        )}

        {f.is_requester && f.status === 'matched' && (
          <View style={styles.section}>
            <Button
              title="잘 마쳤어요"
              disabled={busy || !started}
              onPress={() =>
                confirm('부탁 완료', `${f.helper?.nickname ?? '이웃'}님이 부탁을 잘 마쳤나요?`, '완료', () =>
                  api(`/favors/${id}/complete`, { method: 'POST' }),
                )
              }
            />
            {!started && (
              <ThemedText type="small" themeColor="textSecondary">
                부탁 시간이 되면 누를 수 있어요.
              </ThemedText>
            )}
          </View>
        )}

        {f.status === 'done' &&
          (f.thanks ? (
            <ThemedView type="backgroundElement" style={styles.card}>
              <ThemedText type="smallBold">💌 감사 인사</ThemedText>
              <ThemedText>{f.thanks.message}</ThemedText>
            </ThemedView>
          ) : f.is_requester ? (
            <View style={styles.section}>
              <ThemedText type="smallBold">💌 {f.helper?.nickname}님에게 감사 인사 남기기</ThemedText>
              <TextInput
                value={thanks}
                onChangeText={setThanks}
                maxLength={300}
                multiline
                placeholder="예: 덕분에 콩이가 신나게 산책했어요!"
                placeholderTextColor={theme.textSecondary}
                style={[styles.input, styles.textarea, { color: theme.text, borderColor: theme.border }]}
              />
              <Button
                title="남기기"
                disabled={busy || !thanks.trim()}
                onPress={() => run(() => api(`/favors/${id}/thank`, { method: 'POST', body: { message: thanks.trim() } }))}
              />
            </View>
          ) : null)}

        {/* 이웃: 맡겠다고 신청 */}
        {!f.is_requester && canWrite && f.status === 'open' && (!mine || mine.status === 'cancelled') && (
          <View style={styles.section}>
            {f.can_help ? (
              <>
                <ThemedText type="smallBold">이 부탁 맡기</ThemedText>
                {FAVOR_TERMS.map((t) => (
                  <ThemedText key={t} type="small" themeColor="textSecondary">
                    · {t}
                  </ThemedText>
                ))}
                <Agree checked={agreed} onChange={setAgreed} label="위 내용을 확인했고 동의해요" />
                <TextInput
                  value={message}
                  onChangeText={setMessage}
                  maxLength={200}
                  placeholder="보호자에게 한마디 (선택)"
                  placeholderTextColor={theme.textSecondary}
                  style={[styles.input, { color: theme.text, borderColor: theme.border }]}
                />
                <Button
                  title="제가 할게요"
                  disabled={!agreed}
                  loading={busy}
                  onPress={() =>
                    run(() => api(`/favors/${id}/apply`, { method: 'POST', body: { message: message.trim(), agree_terms: agreed } }))
                  }
                />
              </>
            ) : (
              <ThemedText type="small" themeColor="textSecondary">
                {f.cannot_help_reason}
              </ThemedText>
            )}
          </View>
        )}

        {!f.is_requester && mine && mine.status !== 'cancelled' && (
          <ThemedView type="backgroundElement" style={styles.card}>
            <ThemedText type="smallBold">
              {
                {
                  pending: '신청했어요. 보호자가 확인하면 알려드려요.',
                  accepted: f.status === 'done' ? '잘 마쳤어요. 고마워요!' : '약속이 잡혔어요. 돌봄 시트를 꼭 확인해 주세요.',
                  rejected: '보호자가 다른 이웃과 약속했어요.',
                  cancelled: '',
                }[mine.status]
              }
            </ThemedText>
            {(mine.status === 'pending' || (mine.status === 'accepted' && f.status === 'matched')) && (
              <Button
                title={mine.status === 'accepted' ? '약속 취소' : '신청 취소'}
                variant="secondary"
                disabled={busy}
                onPress={() =>
                  confirm(
                    '신청 취소',
                    mine.status === 'accepted' ? '약속을 취소하면 보호자가 다른 이웃을 다시 찾아야 해요. 취소할까요?' : '신청을 취소할까요?',
                    '취소하기',
                    () => api(`/favors/${id}/withdraw`, { method: 'POST' }),
                    true,
                  )
                }
              />
            )}
          </ThemedView>
        )}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.four, paddingBottom: Spacing.six },
  section: { gap: Spacing.two },
  title: { fontSize: 20, lineHeight: 28, fontWeight: 700 },
  card: { borderRadius: 12, padding: Spacing.three, gap: Spacing.two },
  row: { flexDirection: 'row', gap: Spacing.two },
  half: { flex: 1 },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: Spacing.three, paddingVertical: 12, fontSize: 16 },
  textarea: { minHeight: 80 },
  headerAction: { paddingHorizontal: Spacing.three },
});
