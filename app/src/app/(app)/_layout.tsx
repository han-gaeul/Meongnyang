import { Stack } from 'expo-router';

export default function AppLayout() {
  return (
    <Stack screenOptions={{ headerBackButtonDisplayMode: 'minimal' }}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="posts/[id]" options={{ title: '' }} />
      <Stack.Screen name="posts/new" options={{ title: '글쓰기', presentation: 'modal' }} />
      <Stack.Screen name="gatherings/[id]" options={{ title: '' }} />
      <Stack.Screen name="gatherings/new" options={{ title: '모임 열기', presentation: 'modal' }} />
      <Stack.Screen name="meetup" options={{ title: '만남 인증' }} />
      <Stack.Screen name="neighbors" options={{ title: '내 이웃' }} />
      <Stack.Screen name="pets/new" options={{ title: '반려동물 등록', presentation: 'modal' }} />
    </Stack>
  );
}
