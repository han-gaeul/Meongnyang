import { router } from 'expo-router';
import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import { Chips, ToggleChips } from '@/components/chips';
import { Agree, Button, ErrorText, TextField } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { api, ApiError, type Place, type PlaceCategory } from '@/lib/api';
import { AMENITY_LABEL, PLACE_CATEGORY_LABEL } from '@/lib/format';
import { getCurrentCoords, regionNameOf, type Coords } from '@/lib/location';

type Tri = 'yes' | 'no' | '';
const tri = (v: Tri) => (v === '' ? null : v === 'yes');
const num = (s: string) => (s.trim() === '' ? null : Number(s.replace(/\D/g, '')));

/** 장소 제보. 운영자가 확인한 뒤 지도에 게시된다. */
export default function NewPlace() {
  const [name, setName] = useState('');
  const [category, setCategory] = useState<PlaceCategory>('cafe');
  const [address, setAddress] = useState('');
  const [coords, setCoords] = useState<Coords | null>(null);
  const [region, setRegion] = useState('');
  const [locating, setLocating] = useState(false);
  const [sizes, setSizes] = useState<('S' | 'M' | 'L')[]>([]);
  const [maxWeight, setMaxWeight] = useState('');
  const [space, setSpace] = useState<'' | 'indoor' | 'outdoor' | 'separate'>('');
  const [floor, setFloor] = useState<Tri>('');
  const [fee, setFee] = useState('');
  const [amenities, setAmenities] = useState<string[]>([]);
  const [phone, setPhone] = useState('');
  const [booking, setBooking] = useState('');
  const [is24h, setIs24h] = useState(false);
  const [hours, setHours] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const locate = async () => {
    setLocating(true);
    setError(null);
    try {
      const c = await getCurrentCoords();
      setCoords(c);
      setRegion(await regionNameOf(c).catch(() => ''));
    } catch (e) {
      setError(e instanceof Error ? e.message : '위치를 알 수 없어요.');
    } finally {
      setLocating(false);
    }
  };

  const submit = async () => {
    if (!coords) return;
    setSaving(true);
    setError(null);
    try {
      const p = await api<Place>('/places', {
        method: 'POST',
        body: {
          name: name.trim(),
          category,
          address: address.trim(),
          lat: coords.lat,
          lng: coords.lng,
          region_name: region,
          phone: phone.trim(),
          naver_booking_url: booking.trim(),
          is_24h: is24h,
          hours: hours.trim(),
          sizes_allowed: sizes,
          max_weight_kg: num(maxWeight),
          space,
          floor_ok: tri(floor),
          fee_per_pet: num(fee),
          amenities,
        },
      });
      router.replace({ pathname: '/places/[id]', params: { id: String(p.id) } });
    } catch (e) {
      // 이미 있는 장소면 그 장소로 안내
      if (e instanceof ApiError && e.status === 409) {
        const existing = (e.body as { id?: number }).id;
        if (existing) return router.replace({ pathname: '/places/[id]', params: { id: String(existing) } });
      }
      setError(e instanceof Error ? e.message : '제보하지 못했어요.');
    } finally {
      setSaving(false);
    }
  };

  const isVet = category === 'hospital' || category === 'pharmacy';
  const isEat = category === 'cafe' || category === 'restaurant';

  return (
    <ThemedView style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <ThemedText type="small" themeColor="textSecondary">
          운영자가 확인한 뒤 지도에 올라가요. 아는 것만 채우고 나머지는 비워 두세요.
        </ThemedText>

        <TextField label="이름" value={name} onChangeText={setName} maxLength={100} placeholder="예: 망원동 멍멍카페" />
        <View style={styles.field}>
          <ThemedText type="smallBold">분류</ThemedText>
          <Chips
            value={category}
            onChange={setCategory}
            options={(Object.keys(PLACE_CATEGORY_LABEL) as PlaceCategory[]).map((k) => ({ value: k, label: PLACE_CATEGORY_LABEL[k] }))}
          />
        </View>

        <View style={styles.field}>
          <ThemedText type="smallBold">위치</ThemedText>
          <Button
            title={coords ? `현재 위치로 정했어요${region ? ` (${region})` : ''}` : '지금 여기예요 (현재 위치)'}
            variant={coords ? 'secondary' : 'primary'}
            onPress={locate}
            loading={locating}
          />
          <ThemedText type="small" themeColor="textSecondary">
            장소 앞에서 눌러 주세요. 지도에서 고르는 기능은 다음에 추가할게요.
          </ThemedText>
        </View>
        <TextField label="주소 (선택)" value={address} onChangeText={setAddress} maxLength={200} placeholder="예: 서울 마포구 망원로 00" />

        {!isVet && (
          <ThemedView type="backgroundElement" style={styles.card}>
            <ThemedText type="smallBold">🐾 동반 조건</ThemedText>
            <View style={styles.field}>
              <ThemedText type="small">허용 크기</ThemedText>
              <ToggleChips
                values={sizes}
                onChange={setSizes}
                options={[
                  { value: 'S', label: '소형' },
                  { value: 'M', label: '중형' },
                  { value: 'L', label: '대형' },
                ]}
              />
            </View>
            <TextField label="체중 제한 (kg, 없으면 비움)" value={maxWeight} onChangeText={setMaxWeight} keyboardType="number-pad" maxLength={3} />
            {isEat && (
              <>
                <View style={styles.field}>
                  <ThemedText type="small">동반 공간</ThemedText>
                  <Chips
                    value={space}
                    onChange={setSpace}
                    options={[
                      { value: 'indoor', label: '실내' },
                      { value: 'outdoor', label: '테라스·야외만' },
                      { value: 'separate', label: '전용 공간' },
                      { value: '', label: '모름' },
                    ]}
                  />
                </View>
                <View style={styles.field}>
                  <ThemedText type="small">바닥에 내려놔도 되나요?</ThemedText>
                  <Chips
                    value={floor}
                    onChange={setFloor}
                    options={[
                      { value: 'yes', label: '네' },
                      { value: 'no', label: '안기·켄넬 필수' },
                      { value: '', label: '모름' },
                    ]}
                  />
                </View>
              </>
            )}
            <TextField label="1마리당 추가 요금 (원, 없으면 0)" value={fee} onChangeText={setFee} keyboardType="number-pad" maxLength={7} />
            <View style={styles.field}>
              <ThemedText type="small">편의</ThemedText>
              <ToggleChips values={amenities} onChange={setAmenities} options={Object.entries(AMENITY_LABEL).map(([value, label]) => ({ value, label }))} />
            </View>
          </ThemedView>
        )}

        {isVet && <Agree checked={is24h} onChange={setIs24h} label="24시간 진료해요" />}
        <TextField label="영업시간 (선택)" value={hours} onChangeText={setHours} maxLength={200} placeholder="예: 매일 10:00-21:00, 월 휴무" />
        <TextField label="전화 (선택)" value={phone} onChangeText={setPhone} maxLength={30} keyboardType="phone-pad" />
        <TextField label="네이버 예약 링크 (선택)" value={booking} onChangeText={setBooking} autoCapitalize="none" keyboardType="url" placeholder="https://booking.naver.com/..." />

        <ErrorText message={error} />
        <Button title="제보하기" onPress={submit} loading={saving} disabled={!name.trim() || !coords} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.three, paddingBottom: Spacing.six },
  field: { gap: Spacing.one },
  card: { borderRadius: 12, padding: Spacing.three, gap: Spacing.three },
});
