# Sentinel Android App

The Android client is the explicitly enrolled device in Sentinel's personal safety and recovery system.

## Current capabilities

- Sign in to the Sentinel API
- Pair this Android device to the authenticated account
- Request location permissions
- Collect GPS location using Fused Location Provider
- Send latitude, longitude, accuracy, battery level and timestamp to the backend
- Start/stop foreground-session location updates

## Local development

Open the `mobile/` directory in Android Studio as a Gradle project.

The default API URL is `http://10.0.2.2:8000/`, which points an Android emulator to a FastAPI server running on the development computer.

For a physical phone, replace the API base URL with the development computer's LAN address, or the deployed HTTPS API URL.

## Security note

The mobile client only reports location for a device that the user explicitly authenticated and paired. Camera/evidence features will follow Android permissions and user-consent requirements.
