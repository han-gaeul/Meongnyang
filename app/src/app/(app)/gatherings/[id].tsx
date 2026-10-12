import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Chips } from '@/components/chips';
import { Button, ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';
import { useTheme } from '@/hooks/use-theme';
import { api, type Gathering, type Page, type Participation, type Pet } from '@/lib/api';
import { GATHERING_STATUS_LABEL, KIND_LABEL, SPECIES_LABEL, whenLabel } from '@/lib/format';
import { askReport } from '@/lib/report';

const SIZE = { S: '소형', M: '중형', L: '대형', '': '' } as const;

function petLine(p: Participation['pet']) {
  if (!p) return '';
  return [p.name, p.breed, SIZE[p.size], p.weight_kg ? `${Number(p.weight_kg)}kg` : ''].filter(Boolean).join(' · ');
}

export default function GatheringDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const theme = useTheme();
  const { me } = useSession();
  const canWrite = !!me?.is_verified_member;
  const [g, setG] = useState<Gathering | null>(null);
  const [apps, setApps] = useState<Participation[]>([]);
  const [pets, setPets] = useState<Pet[]>([]);
  const [petId, setPetId] = useState<string>('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api<Gathering>(`/gatherings/${id}`);
      setG(data);
      if (data.is_host) setApps(await api<Participation[]>(`/gatherings/${id}/applications`));
      else if (canWrite && !data.my_participation) {
        const page = await api<Page<Pet>>('/pets');
        const verified = page.results.filter((p) => p.verification_status === 'approved');
        setPets(verified);
        if (verified[0]) setPetId((cur) => cur || String(verified[0].id));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '모임을 불러오지 못했어요.');
    }
  }, [id, canWrite]);

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

  const apply = () =>
    run(() =>
      api(`/gatherings/${id}/apply`, {
        method: 'POST',
        body: { pet: petId ? Number(petId) : null, message: message.trim() },
      }),
    );

  const cancelMine = () =>
    Alert.alert('참여 취소', '이 모임 참여를 취소할까요?', [
      { text: '아니요', style: 'cancel' },
      { text: '취소하기', style: 'destructive', onPress: () => run(() => api(`/gatherings/${id}/cancel`, { method: 'POST' })) },
    ]);

  const decide = (p: Participation, decision: 'accept' | 'reject') =>
    run(() => api(`/gatherings/${id}/applications/${p.id}/${decision}`, { method: 'POST' }));

  const openMenu = () => {
    if (!g) return;
    if (g.is_host) {
      Alert.alert('내 모임', undefined, [
        {
          text: '모임 취소',
          style: 'destructive',
          onPress: () =>
            run(async () => {
              await api(`/gatherings/${id}`, { method: 'DELETE' });
              router.back();
            }),
        },
        { text: '닫기', style: 'cancel' },
      ]);
    } else {
      askReport(`/gatherings/${id}/report`, (hidden) => hidden && router.back());
    }
  };

  const mine = g?.my_participation;
  const isMember = !!g && (g.is_host || mine?.status === 'accepted');
  const pending = apps.filter((a) => a.status === 'pending');

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen
        options={{
          title: g ? KIND_LABEL[g.kind] : '',
          headerRight: () =>
            g && (g.is_host || canWrite) ? (
              <ThemedText type="linkPrimary" onPress={openMenu} accessibilityRole="button" style={styles.headerAction}>
                {g.is_host ? '관리' : '신고'}
              </ThemedText>
            ) : null,
        }}
      />
      <ScrollView contentContainerStyle={styles.container}>
        <ErrorText message={error} />
        {g && (
          <>
            <View style={styles.section}>
              <ThemedText type="smallBold" style={{ color: g.status === 'open' ? theme.primary : theme.textSecondary }}>
                {GATHERING_STATUS_LABEL[g.status]} · {g.accepted_count}/{g.capacity}명
              </ThemedText>
              <ThemedText style={styles.title}>{g.title}</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                {[g.host.nickname, g.region_name || null, g.species !== 'all' ? SPECIES_LABEL[g.species] : null]
                  .filter(Boolean)
                  .join(' · ')}
              </ThemedText>
            </View>

            <ThemedView type="backgroundElement" style={styles.card}>
              <ThemedText type="smallBold">🕖 {whenLabel(g.starts_at)}</ThemedText>
              <ThemedText type="smallBold">📍 {g.place_name}</ThemedText>
            </ThemedView>

            {!!g.content && <ThemedText>{g.content}</ThemedText>}

            <View style={styles.section}>
              <ThemedText type="smallBold">참여하는 이웃 {g.participants.length}</ThemedText>
              {g.participants.length === 0 && (
                <ThemedText type="small" themeColor="textSecondary">
                  아직 수락된 참여자가 없어요.
                </ThemedText>
              )}
              {g.participants.map((p) => (
                <ThemedText key={p.id} type="small">
                  {p.user.nickname}
                  {p.pet ? `  ·  ${petLine(p.pet)}` : ''}
                </ThemedText>
              ))}
            </View>

            {/* 모임장: 신청 관리 */}
            {g.is_host && (
              <View style={styles.section}>
                <ThemedText type="smallBold">받은 신청 {pending.length}</ThemedText>
                {pending.length === 0 && (
                  <ThemedText type="small" themeColor="textSecondary">
                    새 신청이 없어요.
                  </ThemedText>
                )}
                {pending.map((p) => (
                  <ThemedView key={p.id} type="backgroundElement" style={styles.card}>
                    <ThemedText type="smallBold">{p.user.nickname}</ThemedText>
                    {p.pet && <ThemedText type="small">{petLine(p.pet)}</ThemedText>}
                    {!!p.message && <ThemedText type="small">“{p.message}”</ThemedText>}
                    <View style={styles.row}>
                      <View style={styles.half}>
                        <Button title="거절" variant="secondary" onPress={() => decide(p, 'reject')} disabled={busy} />
                      </View>
                      <View style={styles.half}>
                        <Button title="수락" onPress={() => decide(p, 'accept')} disabled={busy || g.status !== 'open'} />
                      </View>
                    </View>
                  </ThemedView>
                ))}
              </View>
            )}

            {/* 참여자: 신청 */}
            {!g.is_host && canWrite && !mine && g.status === 'open' && (
              <View style={styles.section}>
                <ThemedText type="smallBold">참여 신청</ThemedText>
                {pets.length > 0 && (
                  <Chips
                    value={petId}
                    onChange={setPetId}
                    options={[...pets.map((p) => ({ value: String(p.id), label: p.name })), { value: '', label: '혼자 갈게요' }]}
                  />
                )}
                <TextInput
                  value={message}
                  onChangeText={setMessage}
                  maxLength={200}
                  placeholder="모임장에게 한마디 (선택)"
                  placeholderTextColor={theme.textSecondary}
                  style={[styles.input, { color: theme.text, borderColor: theme.border }]}
                />
                <Button title={g.kind === 'share' ? '받고 싶어요' : '참여 신청하기'} onPress={apply} loading={busy} />
              </View>
            )}

            {!g.is_host && mine && (
              <ThemedView type="backgroundElement" style={styles.card}>
                <ThemedText type="smallBold">
                  {
                    {
                      pending: '신청했어요. 모임장이 확인하면 알려드려요.',
                      accepted: '참여가 확정됐어요!',
                      rejected: '이번 모임에는 함께하지 못하게 됐어요.',
                      cancelled: '참여를 취소했어요.',
                    }[mine.status]
                  }
                </ThemedText>
                {(mine.status === 'pending' || mine.status === 'accepted') && (
                  <Button title="참여 취소" variant="secondary" onPress={cancelMine} disabled={busy} />
                )}
              </ThemedView>
            )}

            {isMember && g.status !== 'cancelled' && (
              <View style={styles.section}>
                <Button
                  title="만나서 QR로 만남 인증하기"
                  onPress={() => router.push({ pathname: '/meetup', params: { gathering: String(g.id) } })}
                />
                <ThemedText type="small" themeColor="textSecondary">
                  모임장이 QR을 띄우고 참여자가 찍으면 한 번에 인증돼요.
                </ThemedText>
              </View>
            )}
          </>
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
  headerAction: { paddingHorizontal: Spacing.three },
});
