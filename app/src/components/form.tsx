import { ActivityIndicator, Pressable, StyleSheet, TextInput, View, type TextInputProps } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export function TextField({ label, ...props }: TextInputProps & { label: string }) {
  const theme = useTheme();
  return (
    <View style={styles.field}>
      <ThemedText type="smallBold">{label}</ThemedText>
      <TextInput
        placeholderTextColor={theme.textSecondary}
        style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.background }]}
        {...props}
      />
    </View>
  );
}

export function Button({
  title,
  onPress,
  loading,
  variant = 'primary',
  disabled,
}: {
  title: string;
  onPress: () => void;
  loading?: boolean;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}) {
  const theme = useTheme();
  const primary = variant === 'primary';
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor: primary ? theme.primary : theme.background,
          borderWidth: primary ? 0 : 1,
          borderColor: theme.border,
          opacity: disabled ? 0.5 : pressed ? 0.85 : 1,
        },
      ]}>
      {loading ? (
        <ActivityIndicator color={primary ? theme.onPrimary : theme.text} />
      ) : (
        <ThemedText type="smallBold" style={{ color: primary ? theme.onPrimary : theme.text }}>
          {title}
        </ThemedText>
      )}
    </Pressable>
  );
}

/** 명시적 동의 체크. 화면을 연 것만으로는 동의로 치지 않는다. */
export function Agree({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      onPress={() => onChange(!checked)}
      style={styles.agree}>
      <View
        style={[
          styles.box,
          { borderColor: checked ? theme.primary : theme.border, backgroundColor: checked ? theme.primary : 'transparent' },
        ]}>
        {checked && <ThemedText style={{ color: theme.onPrimary, fontSize: 14, lineHeight: 18 }}>✓</ThemedText>}
      </View>
      <ThemedText type="small" style={styles.flex}>
        {label}
      </ThemedText>
    </Pressable>
  );
}

export function ErrorText({ message }: { message: string | null }) {
  const theme = useTheme();
  if (!message) return null;
  return (
    <ThemedText type="small" style={{ color: theme.danger }}>
      {message}
    </ThemedText>
  );
}

const styles = StyleSheet.create({
  field: { gap: Spacing.one },
  flex: { flex: 1 },
  agree: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.one },
  box: { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center' },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: Spacing.three,
    paddingVertical: 12,
    fontSize: 16,
  },
  button: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
});
