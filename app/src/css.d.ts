// expo start가 만드는 expo-env.d.ts가 없을 때(CI)도 타입체크가 되도록 CSS import를 선언
declare module '*.css';
