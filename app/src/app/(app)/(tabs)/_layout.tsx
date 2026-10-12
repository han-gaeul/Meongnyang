import { Tabs } from 'expo-router';
import { Text } from 'react-native';

import { useTheme } from '@/hooks/use-theme';

// 아이콘 세트는 디자인 확정 후 교체. 지금은 이모지로 자리만 잡는다.
const icon = (glyph: string) =>
  function TabIcon({ focused }: { focused: boolean }) {
    return <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.45 }}>{glyph}</Text>;
  };

export default function TabLayout() {
  const theme = useTheme();
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: theme.primary,
        tabBarInactiveTintColor: theme.textSecondary,
      }}>
      <Tabs.Screen name="index" options={{ title: '홈', headerShown: false, tabBarIcon: icon('🏠') }} />
      <Tabs.Screen name="gatherings" options={{ title: '모임', tabBarIcon: icon('🐾') }} />
      <Tabs.Screen name="map" options={{ title: '지도', tabBarIcon: icon('📍') }} />
      <Tabs.Screen name="journal" options={{ title: '일기', tabBarIcon: icon('📔') }} />
      <Tabs.Screen name="my" options={{ title: '마이', headerShown: false, tabBarIcon: icon('🙂') }} />
    </Tabs>
  );
}
