import { CameraView, useCameraPermissions, type BarcodeScanningResult } from 'expo-camera';
import { router, Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import { Chips } from '@/components/chips';
import { Button, ErrorText } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { api, type Neighbor } from '@/lib/api';
import { LEVEL_LABEL } from '@/lib/format';
import { getCurrentCoords } from '@/lib/location';

type Mode = 'show' | 'scan';
const REFRESH_MS = 150_000; // 서버 QR 유효 시간(180초)보다 조금 일찍 새로 받기

export default function Meetup() {
  const { gathering } = useLocalSearchParams<{ gathering?: string }>();
  const [mode, setMode] = useState<Mode>('show');

  return (
    <ThemedView style={styles.flex}>
      <Stack.Screen options={{ title: '만남 인증' }} />
      <View style={styles.container}>
        <Chips
          value={mode}
          onChange={setMode}
          options={[
            { value: 'show', label: '내 QR 보여주기' },
            { value: 'scan', label: '상대 QR 찍기' },
          ]}
        />
        {mode === 'show' ? <ShowQR gathering={gathering} /> : <ScanQR />}
      </View>
    </ThemedView>
  );
}

function ShowQR({ gathering }: { gathering?: string }) {
  const [qr, setQr] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const issue = useCallback(async () => {
    setError(null);
    try {
      const coords = await getCurrentCoords();
      const res = await api<{ qr: string }>('/meetups/token', {
        method: 'POST',
        body: { ...coords, gathering: gathering ? Number(gathering) : null },
      });
      setQr(res.qr);
    } catch (e) {
      setQr(null);
      setError(e instanceof Error ? e.message : 'QR을 만들지 못했어요.');
    }
  }, [gathering]);

  // 화면에 있는 동안 QR을 주기적으로 새로 받는다
  useFocusEffect(
    useCallback(() => {
      issue();
      const timer = setInterval(issue, REFRESH_MS);
      return () => clearInterval(timer);
    }, [issue]),
  );

  return (
    <View style={styles.center}>
      <ThemedText type="small" themeColor="textSecondary" style={styles.centerText}>
        같은 자리에 있는 이웃이 이 QR을 찍으면 만남이 기록돼요.{'\n'}여러 명이 같은 QR을 찍어도 돼요.
      </ThemedText>
      <View style={styles.qrBox}>
        {qr ? <QRCode value={qr} size={240} backgroundColor="#ffffff" color="#1F1A17" /> : !error && <ActivityIndicator />}
      </View>
      <ErrorText message={error} />
      {error && <Button title="다시 시도" variant="secondary" onPress={issue} />}
      <ThemedText type="small" themeColor="textSecondary">
        QR은 몇 분마다 자동으로 바뀌어요.
      </ThemedText>
    </View>
  );
}

function ScanQR() {
  const [permission, requestPermission] = useCameraPermissions();
  const [result, setResult] = useState<{ created: boolean; neighbor: Neighbor } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const handling = useRef(false);

  useEffect(() => {
    if (permission && !permission.granted && permission.canAskAgain) requestPermission();
  }, [permission, requestPermission]);

  const onScanned = async ({ data }: BarcodeScanningResult) => {
    if (handling.current || result) return;
    handling.current = true;
    setBusy(true);
    setError(null);
    try {
      const coords = await getCurrentCoords();
      setResult(await api('/meetups/confirm', { method: 'POST', body: { qr: data, ...coords } }));
    } catch (e) {
      setError(e instanceof Error ? e.message : '인증하지 못했어요.');
      // 잘못 찍은 경우 잠시 뒤 다시 찍을 수 있게
      setTimeout(() => {
        handling.current = false;
      }, 2000);
    } finally {
      setBusy(false);
    }
  };

  if (!permission) return <ActivityIndicator style={styles.spinner} />;
  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <ThemedText type="small" style={styles.centerText}>
          QR을 찍으려면 카메라 권한이 필요해요.
        </ThemedText>
        <Button title="카메라 허용하기" onPress={requestPermission} />
      </View>
    );
  }

  if (result) {
    const n = result.neighbor;
    return (
      <View style={styles.center}>
        <ThemedText style={styles.big}>🐾</ThemedText>
        <ThemedText type="subtitle" style={styles.centerText}>
          {n.nickname}님
        </ThemedText>
        <ThemedText style={styles.centerText}>
          {result.created ? `${n.meet_count}번째 만남이 기록됐어요!` : '오늘은 이미 인증한 이웃이에요.'}
        </ThemedText>
        {!!LEVEL_LABEL[n.level] && (
          <ThemedText type="smallBold" style={styles.centerText}>
            지금 단계: {LEVEL_LABEL[n.level]}
          </ThemedText>
        )}
        <Button title="이웃 목록 보기" onPress={() => router.replace('/neighbors')} />
        <Button
          title="다른 이웃 QR 찍기"
          variant="secondary"
          onPress={() => {
            setResult(null);
            handling.current = false;
          }}
        />
      </View>
    );
  }

  return (
    <View style={styles.scanWrap}>
      <CameraView
        style={styles.camera}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
        onBarcodeScanned={busy ? undefined : onScanned}
      />
      {busy && <ActivityIndicator style={styles.spinner} />}
      <ErrorText message={error} />
      <ThemedText type="small" themeColor="textSecondary" style={styles.centerText}>
        상대 화면의 QR을 네모 안에 맞춰 주세요. 위치 확인을 위해 같은 자리에서 찍어야 해요.
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { flex: 1, padding: Spacing.four, gap: Spacing.four },
  center: { alignItems: 'stretch', gap: Spacing.three, paddingTop: Spacing.three },
  centerText: { textAlign: 'center' },
  qrBox: {
    alignSelf: 'center',
    width: 272,
    height: 272,
    borderRadius: 16,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  scanWrap: { flex: 1, gap: Spacing.three },
  camera: { width: '100%', aspectRatio: 1, borderRadius: 16, overflow: 'hidden' },
  spinner: { marginVertical: Spacing.three },
  big: { fontSize: 48, lineHeight: 56, textAlign: 'center' },
});
