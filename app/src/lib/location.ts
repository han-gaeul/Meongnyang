import * as Location from 'expo-location';

export type Coords = { lat: number; lng: number };

export class LocationError extends Error {}

/** 현재 위치. 권한이 없으면 요청하고, 거부되면 안내 메시지로 실패한다. */
export async function getCurrentCoords(): Promise<Coords> {
  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status !== 'granted') {
    throw new LocationError('위치 권한이 필요해요. 설정에서 멍냥동네(Expo Go)의 위치 접근을 허용해 주세요.');
  }
  const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
  return { lat: pos.coords.latitude, lng: pos.coords.longitude };
}

/** 좌표 → 동네 이름 (예: 망원동). 못 찾으면 구·시 단위로. */
export async function regionNameOf({ lat, lng }: Coords): Promise<string> {
  const [addr] = await Location.reverseGeocodeAsync({ latitude: lat, longitude: lng });
  return addr?.district || addr?.subregion || addr?.city || '';
}
