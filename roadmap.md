# Bacy 10 engineering status

## Existing foundations
- [x] Voice-first React application and responsive HUD.
- [x] Server-side AI conversation through Lovable AI Gateway.
- [x] Real generated speech endpoint and browser microphone recognition.
- [x] Backup voice studio and voice-provider status checks.
- [x] Protected, read-only Gmail metadata endpoint for the LiveKit agent.
- [x] Local browser conversation continuity (not cloud memory).

## Remaining verification and engineering
- [ ] Reconcile and validate the outstanding V4.0 LiveKit/Android restoration PR without force-merging.
- [ ] Run build, tests, lint and LiveKit source-package validation on the integrated branch.
- [ ] Verify real microphone input and generated speech on Android Chrome and desktop browsers.
- [ ] Verify hosting secrets and connected services without exposing secret values.
- [ ] Implement authenticated, user-controlled cloud memory with retention and deletion controls.
- [ ] Add integration tests for voice-provider failures, browser storage restrictions and Gmail authorization.
- [ ] Verify production deployment and installed PWA update behaviour.
