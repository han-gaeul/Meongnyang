import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, ErrorText, TextField } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';
import { api, type Page, type Pet } from '@/lib/api';

const STATUS_LABEL: Record<Pet['verification_status'], string> = {
  unverified: '미인증',
  pending: '검토 대기',
  approved: '인증 완료',
  rejected: '인증 실패',
};
const SIZE_LABEL = { S: '소형', M: '중형', L: '대형', '': '' } as const;

export default function My() {
  const { me, reloadMe, signOut } = useSession();
  const [pets, setPets] = useState<Pet[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [page] = await Promise.all([api<Page<Pet>>('/pets'), reloadMe()]);
      setPets(page.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : '불러오지 못했습니다.');
    }
  }, [reloadMe]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const verifyIdentity = async () => {
    // TODO: PortOne 본인인증 창 → 받은 거래 ID를 서버로 전송. 지금은 개발용 mock.
    setVerifying(true);
    try {
      await api('/auth/identity/verify', {
        method: 'POST',
        body: { transaction_id: `mock-ok-${me?.id}` },
      });
      await reloadMe();
    } catch (e) {
      setError(e instanceof Error ? e.message : '본인인증에 실패했습니다.');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <ThemedView style={styles.flex}>
      <SafeAreaView style={styles.flex} edges={['top']}>
        <ScrollView
          contentContainerStyle={styles.container}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={async () => {
                setRefreshing(true);
                await load();
                setRefreshing(false);
              }}
            />
          }>
          <View style={styles.section}>
            <ThemedText type="subtitle">{me?.nickname ?? ' '}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              {me?.is_verified_member
                ? '인증 완료 회원 · 모든 기능 이용 가능'
                : '본인인증과 반려동물 인증을 마치면 모임과 부탁을 이용할 수 있어요.'}
            </ThemedText>
          </View>

          <ThemedView type="backgroundElement" style={styles.card}>
            <ThemedText type="smallBold">휴대폰 본인인증</ThemedText>
            {me?.is_identity_verified ? (
              <ThemedText type="small">인증 완료</ThemedText>
            ) : (
              <Button title={__DEV__ ? '본인인증 (개발용 mock)' : '본인인증 하기'} onPress={verifyIdentity} loading={verifying} />
            )}
          </ThemedView>

          <View style={styles.section}>
            <View style={styles.row}>
              <ThemedText type="smallBold">내 반려동물</ThemedText>
              <ThemedText type="linkPrimary" onPress={() => router.push('/pets/new')}>
                + 등록
              </ThemedText>
            </View>
            {pets.length === 0 && (
              <ThemedText type="small" themeColor="textSecondary">
                아직 등록된 반려동물이 없어요.
              </ThemedText>
            )}
            {pets.map((pet) => (
              <PetCard key={pet.id} pet={pet} canVerify={!!me?.is_identity_verified} onChanged={load} />
            ))}
          </View>

          <ErrorText message={error} />
          <Button title="로그아웃" variant="secondary" onPress={signOut} />
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

function PetCard({ pet, canVerify, onChanged }: { pet: Pet; canVerify: boolean; onChanged: () => void }) {
  const [regNo, setRegNo] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const needsVerify = pet.verification_status === 'unverified' || pet.verification_status === 'rejected';

  const verify = async () => {
    setBusy(true);
    setError(null);
    try {
      await api(`/pets/${pet.id}/verify`, { method: 'POST', body: { registration_number: regNo.trim() } });
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : '인증에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  };

  const details = [
    pet.species === 'dog' ? '강아지' : '고양이',
    pet.breed,
    SIZE_LABEL[pet.size],
    pet.weight_kg ? `${Number(pet.weight_kg)}kg` : '',
    pet.age != null ? `${pet.age}살` : '',
  ].filter(Boolean);

  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <View style={styles.row}>
        <ThemedText type="smallBold">{pet.name}</ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          {STATUS_LABEL[pet.verification_status]}
        </ThemedText>
      </View>
      <ThemedText type="small" themeColor="textSecondary">
        {details.join(' · ')}
      </ThemedText>
      {needsVerify && canVerify && (
        <>
          <TextField
            label="동물등록번호 (15자리)"
            value={regNo}
            onChangeText={setRegNo}
            keyboardType="number-pad"
            maxLength={15}
          />
          <ErrorText message={error} />
          <Button title="등록번호로 인증" onPress={verify} loading={busy} disabled={regNo.length !== 15} />
        </>
      )}
      {pet.verification_status === 'pending' && (
        <ThemedText type="small" themeColor="textSecondary">
          등록정보가 조회되지 않아 운영자가 확인 중이에요.
        </ThemedText>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.four },
  section: { gap: Spacing.two },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  card: { borderRadius: 14, padding: Spacing.three, gap: Spacing.two },
});
