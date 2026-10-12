import { Alert } from 'react-native';

import { api, type ReportReason } from './api';

const REASONS: { value: ReportReason; label: string }[] = [
  { value: 'money', label: '금전 요구' },
  { value: 'spam', label: '광고·도배' },
  { value: 'abuse', label: '욕설·비하' },
  { value: 'danger', label: '동물 학대·위험' },
  { value: 'other', label: '기타' },
];

/** 신고 사유를 고르게 하고 서버에 보낸다. path 예: '/posts/3/report' */
export function askReport(path: string, onDone?: (hidden: boolean) => void) {
  Alert.alert('신고하기', '어떤 문제가 있나요?', [
    ...REASONS.map((r) => ({
      text: r.label,
      onPress: async () => {
        try {
          const res = await api<{ created: boolean; hidden: boolean }>(path, {
            method: 'POST',
            body: { reason: r.value },
          });
          Alert.alert(res.created ? '신고가 접수되었어요.' : '이미 신고한 글이에요.');
          onDone?.(res.hidden);
        } catch (e) {
          Alert.alert('신고하지 못했어요', e instanceof Error ? e.message : undefined);
        }
      },
    })),
    { text: '취소', style: 'cancel' },
  ]);
}
