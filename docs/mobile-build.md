# Mobile Build

Use Expo/EAS with `mobile/eas.json`.

Production requirements:

- Set `EXPO_PUBLIC_ENV=production`.
- Set `EXPO_PUBLIC_API_URL=https://<api-host>/api/v1`.
- Native WebRTC/calling still requires a provider choice, native module validation, app permissions review, and real device QA.
- Push notifications require provider credentials and device-token delivery testing.

Useful checks:

```sh
cd mobile
npm run typecheck
npm test
npx expo-doctor
npx eas-cli build:configure --non-interactive
```
