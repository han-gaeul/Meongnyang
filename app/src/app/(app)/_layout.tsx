import { Stack } from 'expo-router';

export default function AppLayout() {
  return (
    <Stack screenOptions={{ headerBackButtonDisplayMode: 'minimal' }}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="posts/[id]" options={{ title: '' }} />
      <Stack.Screen name="posts/new" options={{ title: '글쓰기', presentation: 'modal' }} />
      <Stack.Screen name="pets/new" options={{ title: '반려동물 등록', presentation: 'modal' }} />
    </Stack>
  );
}
