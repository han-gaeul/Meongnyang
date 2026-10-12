import { useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';

import { Button, ErrorText, TextField } from '@/components/form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useSession } from '@/ctx';

export default function SignUp() {
  const { signUp } = useSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError(null);
    setLoading(true);
    try {
      await signUp(email.trim(), password, nickname.trim());
    } catch (e) {
      setError(e instanceof Error ? e.message : '가입에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThemedView style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <ThemedText themeColor="textSecondary">
          가입 후 휴대폰 본인인증과 반려동물 인증을 마치면 모든 기능을 쓸 수 있어요.
        </ThemedText>
        <TextField label="이메일" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
        <TextField label="비밀번호" value={password} onChangeText={setPassword} secureTextEntry autoComplete="new-password" />
        <TextField label="닉네임" value={nickname} onChangeText={setNickname} maxLength={20} placeholder="예: 콩이보호자" />
        <ErrorText message={error} />
        <Button title="가입하기" onPress={submit} loading={loading} disabled={!email || !password || !nickname} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: Spacing.four, gap: Spacing.three },
});
