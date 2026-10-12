import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { Button, ErrorText, TextField } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { api, type Pet } from '@/lib/api';

function Choice<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T | '';
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  const theme = useTheme();
  return (
    <View style={styles.field}>
      <ThemedText type="smallBold">{label}</ThemedText>
      <View style={styles.chips}>
        {options.map((o) => {
          const selected = o.value === value;
          return (
            <Pressable
              key={o.value}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              onPress={() => onChange(o.value)}
              style={[
                styles.chip,
                {
                  borderColor: selected ? theme.primary : theme.border,
                  backgroundColor: selected ? theme.primary : 'transparent',
                },
              ]}>
              <ThemedText type="small" style={{ color: selected ? theme.onPrimary : theme.text }}>
                {o.label}
              </ThemedText>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export default function NewPet() {
  const [name, setName] = useState('');
  const [species, setSpecies] = useState<Pet['species'] | ''>('');
  const [size, setSize] = useState<Exclude<Pet['size'], ''> | ''>('');
  const [weight, setWeight] = useState('');
  const [breed, setBreed] = useState('');
  const [birthday, setBirthday] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError(null);
    setLoading(true);
    try {
      await api<Pet>('/pets', {
        method: 'POST',
        body: {
          name: name.trim(),
          species,
          size,
          breed: breed.trim(),
          weight_kg: weight ? weight : null,
          birthday: birthday || null,
        },
      });
      router.back();
    } catch (e) {
      setError(e instanceof Error ? e.message : '등록에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThemedView style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <TextField label="이름" value={name} onChangeText={setName} maxLength={25} />
        <Choice
          label="종"
          value={species}
          onChange={setSpecies}
          options={[
            { value: 'dog', label: '강아지' },
            { value: 'cat', label: '고양이' },
          ]}
        />
        <TextField label="품종" value={breed} onChangeText={setBreed} placeholder="예: 골든 리트리버" />
        <Choice
          label="크기"
          value={size}
          onChange={setSize}
          options={[
            { value: 'S', label: '소형' },
            { value: 'M', label: '중형' },
            { value: 'L', label: '대형' },
          ]}
        />
        <TextField label="몸무게 (kg)" value={weight} onChangeText={setWeight} keyboardType="decimal-pad" placeholder="예: 28.5" />
        <TextField label="생일" value={birthday} onChangeText={setBirthday} placeholder="YYYY-MM-DD" maxLength={10} />
        <ThemedText type="small" themeColor="textSecondary">
          크기와 몸무게는 &quot;우리 아이가 갈 수 있는 곳&quot; 필터에 쓰여요.
        </ThemedText>
        <ErrorText message={error} />
        <Button title="등록하기" onPress={submit} loading={loading} disabled={!name || !species} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.three },
  field: { gap: Spacing.one },
  chips: { flexDirection: 'row', gap: Spacing.two, flexWrap: 'wrap' },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: Spacing.three, paddingVertical: Spacing.two },
});
