import { Stack } from 'expo-router';

export default function AppLayout() {
  return (
    <Stack screenOptions={{ headerBackButtonDisplayMode: 'minimal' }}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="posts/[id]" options={{ title: '' }} />
      <Stack.Screen name="posts/new" options={{ title: '글쓰기', presentation: 'modal' }} />
      <Stack.Screen name="gatherings/[id]" options={{ title: '' }} />
      <Stack.Screen name="gatherings/new" options={{ title: '모임 열기', presentation: 'modal' }} />
      <Stack.Screen name="favors/[id]" options={{ title: '' }} />
      <Stack.Screen name="favors/new" options={{ title: '부탁하기', presentation: 'modal' }} />
      <Stack.Screen name="places/[id]" options={{ title: '' }} />
      <Stack.Screen name="places/new" options={{ title: '장소 제보', presentation: 'modal' }} />
      <Stack.Screen name="places/review" options={{ title: '30초 후기', presentation: 'modal' }} />
      <Stack.Screen name="journal/[id]" options={{ title: '' }} />
      <Stack.Screen name="journal/new" options={{ title: '', presentation: 'modal' }} />
      <Stack.Screen name="journal/walk" options={{ title: '산책' }} />
      <Stack.Screen name="meetup" options={{ title: '만남 인증' }} />
      <Stack.Screen name="neighbors" options={{ title: '내 이웃' }} />
      <Stack.Screen name="pets/new" options={{ title: '반려동물 등록', presentation: 'modal' }} />
    </Stack>
  );
}
