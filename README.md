# Sentinel AI – Personal Safety & Device Recovery Platform

Sentinel is a privacy-first platform for personal safety, emergency response, journey monitoring, and recovery of user-owned enrolled devices.

## Vision

Sentinel combines:

- Personal safety and SOS workflows
- Guardian-assisted journey monitoring
- Location and geofence intelligence
- AI-based risk and anomaly detection
- Emergency evidence workflows
- Authorized personal-device recovery

## Core Modules

1. **Personal Safety** – SOS, check-ins, emergency contacts, emergency mode
2. **Journey Intelligence** – planned journeys, ETA, route deviation, safe-arrival confirmation
3. **AI Risk Engine** – anomaly detection and configurable risk scoring
4. **Emergency Response** – alerts, escalation, guardian workflow, emergency resources
5. **Device Recovery** – enrolled-device tracking, lock/alarm/recovery status
6. **Web Dashboard** – live status, maps, alerts, journeys, devices, audit events

## Privacy & Security Principles

- Only explicitly enrolled/authorized devices can be controlled.
- Camera/evidence functionality must respect operating-system permissions and user consent.
- Sensitive data should be encrypted in transit and protected at rest.
- Every security-sensitive action is audit logged.
- Emergency automation must minimize false positives and provide configurable escalation.

## Repository Structure

```text
sentinel-ai-personal-safety/
├── backend/          # FastAPI backend and domain services
├── dashboard/        # React web dashboard
├── mobile/           # Android application
├── docs/             # Architecture, API, security and product docs
├── .github/          # CI/CD configuration
└── README.md
```

## MVP Roadmap

### MVP-01

- User authentication
- Device enrollment/pairing
- Guardian contacts
- Location updates
- SOS event creation
- Guardian notification
- Basic live dashboard

### MVP-02

- Safe Journey Mode
- Check-in system
- Geofencing
- Escalation rules
- Journey timeline

### MVP-03

- AI risk scoring
- Movement anomaly detection
- Route deviation intelligence
- Risk explanations

### MVP-04

- Device recovery controls
- Evidence workflow
- Advanced dashboard
- Security hardening

## Status

🚧 Initial project setup
