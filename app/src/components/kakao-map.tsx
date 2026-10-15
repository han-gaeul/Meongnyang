import { useEffect, useMemo, useRef, useState } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';

import { ThemedText } from '@/components/themed-text';
import { KAKAO_JS_KEY, KAKAO_MAP_ORIGIN } from '@/lib/config';
import type { Coords } from '@/lib/location';

export type MapMarker = { id: number; lat: number; lng: number; label: string; tone: 'yes' | 'no' | 'unknown' };

type Props = {
  center: Coords;
  markers: MapMarker[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  /** 지도를 움직여 중심이 바뀌었을 때 */
  onMove?: (center: Coords) => void;
  /** 산책 경로 [[lat, lng], ...] */
  path?: [number, number][];
  /** 경로 전체가 보이게 맞춘다 (기록 끝난 산책 보기) */
  fitPath?: boolean;
};

/** 카카오맵을 쓸 수 있는가 (키가 있고 앱에서 실행 중) */
export const kakaoMapAvailable = !!KAKAO_JS_KEY && Platform.OS !== 'web';

/**
 * 카카오맵 JavaScript SDK를 WebView로 띄운다.
 * Expo Go에서도 동작하도록 네이티브 SDK 대신 JS SDK를 쓴다.
 */
export function KakaoMap({ center, markers, selectedId, onSelect, onMove, path, fitPath }: Props) {
  const ref = useRef<WebView>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  // 처음 중심만 HTML에 넣는다. 이후 중심 이동은 injectJavaScript로.
  const [initial] = useState(center);
  const html = useMemo(() => buildHtml(initial), [initial]);

  useEffect(() => {
    if (ready) ref.current?.injectJavaScript(`window.setMarkers(${JSON.stringify(markers)}, ${selectedId ?? 'null'}); true;`);
  }, [ready, markers, selectedId]);

  useEffect(() => {
    if (ready) ref.current?.injectJavaScript(`window.moveTo(${center.lat}, ${center.lng}); true;`);
  }, [ready, center.lat, center.lng]);

  useEffect(() => {
    if (ready && path) ref.current?.injectJavaScript(`window.setPath(${JSON.stringify(path)}, ${fitPath ? 'true' : 'false'}); true;`);
  }, [ready, path, fitPath]);

  const onMessage = (e: WebViewMessageEvent) => {
    try {
      const msg = JSON.parse(e.nativeEvent.data);
      if (msg.type === 'ready') setReady(true);
      else if (msg.type === 'select') onSelect(msg.id);
      else if (msg.type === 'moved') onMove?.({ lat: msg.lat, lng: msg.lng });
      else if (msg.type === 'error') setFailed(msg.message);
    } catch {
      // 무시
    }
  };

  return (
    <View style={styles.wrap}>
      <WebView
        ref={ref}
        originWhitelist={['*']}
        source={{ html, baseUrl: KAKAO_MAP_ORIGIN }}
        onMessage={onMessage}
        javaScriptEnabled
        style={styles.web}
      />
      {failed && (
        <View style={styles.error}>
          <ThemedText type="small">지도를 불러오지 못했어요. {failed}</ThemedText>
        </View>
      )}
    </View>
  );
}

function buildHtml(c: Coords) {
  return `<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>
  html,body,#map{margin:0;padding:0;width:100%;height:100%}
  .pin{transform:translateY(-6px);padding:4px 8px;border-radius:12px;font:600 12px -apple-system,system-ui,sans-serif;
       white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.25);border:2px solid #fff;max-width:140px;overflow:hidden;text-overflow:ellipsis}
  .yes{background:#E07B39;color:#fff}.unknown{background:#fff;color:#333;border-color:#ccc}.no{background:#bbb;color:#fff}
  .sel{transform:translateY(-6px) scale(1.15);z-index:10;outline:3px solid #2b2b2b}
</style></head><body><div id="map"></div>
<script>
  function post(m){ window.ReactNativeWebView && window.ReactNativeWebView.postMessage(JSON.stringify(m)); }
  window.onerror = function(msg){ post({type:'error', message:String(msg)}); };
</script>
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_JS_KEY}&autoload=false"
  onerror="post({type:'error', message:'카카오 지도 스크립트를 받지 못했어요. 키와 도메인 등록을 확인해 주세요.'})"></script>
<script>
  var map, overlays = [], moveTimer = null, programmatic = false;
  kakao.maps.load(function(){
    map = new kakao.maps.Map(document.getElementById('map'), { center: new kakao.maps.LatLng(${c.lat}, ${c.lng}), level: 5 });
    kakao.maps.event.addListener(map, 'idle', function(){
      if (programmatic) { programmatic = false; return; }
      clearTimeout(moveTimer);
      moveTimer = setTimeout(function(){ var p = map.getCenter(); post({type:'moved', lat:p.getLat(), lng:p.getLng()}); }, 300);
    });
    post({type:'ready'});
  });
  window.moveTo = function(lat, lng){ if(!map) return; programmatic = true; map.setCenter(new kakao.maps.LatLng(lat, lng)); };
  var line = null;
  window.setPath = function(pts, fit){
    if(!map) return;
    var latlngs = pts.map(function(p){ return new kakao.maps.LatLng(p[0], p[1]); });
    if(!line){ line = new kakao.maps.Polyline({ strokeWeight: 6, strokeColor: '#E07B39', strokeOpacity: 0.9 }); line.setMap(map); }
    line.setPath(latlngs);
    if(fit && latlngs.length > 1){
      var b = new kakao.maps.LatLngBounds(); latlngs.forEach(function(l){ b.extend(l); });
      programmatic = true; map.setBounds(b, 40, 40, 40, 40);
    } else if(latlngs.length){ programmatic = true; map.panTo(latlngs[latlngs.length - 1]); }
  };
  window.setMarkers = function(list, selected){
    overlays.forEach(function(o){ o.setMap(null); }); overlays = [];
    list.forEach(function(m){
      var el = document.createElement('div');
      el.className = 'pin ' + m.tone + (m.id === selected ? ' sel' : '');
      el.textContent = m.label;
      el.onclick = function(){ post({type:'select', id:m.id}); };
      var o = new kakao.maps.CustomOverlay({ position: new kakao.maps.LatLng(m.lat, m.lng), content: el, yAnchor: 1, zIndex: m.id === selected ? 10 : 1 });
      o.setMap(map); overlays.push(o);
    });
  };
</script></body></html>`;
}

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  web: { flex: 1 },
  error: { position: 'absolute', left: 12, right: 12, bottom: 12, padding: 10, borderRadius: 10, backgroundColor: '#fff' },
});
