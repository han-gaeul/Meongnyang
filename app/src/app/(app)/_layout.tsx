import { Stack } from 'expo-router';

export default function AppLayout() {
  return (
    <Stack>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="pets/new" options={{ title: '반려동물 등록', presentation: 'modal' }} />
    </Stack>
  );
}
