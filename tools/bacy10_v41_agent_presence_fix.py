"""BACY-10 V4.1: distinguish a LiveKit room connection from a joined voice agent.

A room can connect before the BACY-10 worker joins. The previous UI treated any
connected room as "LISTENING", hiding the real failure and offering no retry.
This patch surfaces agent presence, allows a safe room reconnect, and clears the
waiting notice when the actual agent participant arrives.
"""
from pathlib import Path

def one(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"V4.1 agent-presence patch expected one anchor in {path}, found {count}: {old[:100]!r}"
        )
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def apply(root: Path) -> None:
    mobile = root / "mobile/lib"
    ctrl = mobile / "controllers/app_ctrl.dart"

    one(
        ctrl,
        """    if (isSessionStarting || session.connectionState == sdk.ConnectionState.connected
        || session.connectionState == sdk.ConnectionState.reconnecting) {
      return;
    }""",
        """    if (isSessionStarting || session.connectionState == sdk.ConnectionState.reconnecting) {
      return;
    }
    if (session.connectionState == sdk.ConnectionState.connected &&
        room.agentParticipant != null) {
      return;
    }
    if (session.connectionState == sdk.ConnectionState.connected &&
        room.agentParticipant == null) {
      _logger.warning('LiveKit room connected without the BACY-10 agent; restarting the session.');
      await disconnect();
    }""",
    )
    one(ctrl, "while (room.remoteParticipants.isEmpty &&", "while (room.agentParticipant == null &&")
    one(ctrl, "if (room.remoteParticipants.isEmpty) {", "if (room.agentParticipant == null) {")

    one(
        ctrl,
        """  String _lastCompactStatus = '';""",
        """  String _lastCompactStatus = '';
  bool _lastAgentJoined = false;""",
    )
    one(
        ctrl,
        """    final state = session.connectionState != sdk.ConnectionState.connected
        ? 'DISCONNECTED'
        : room.localParticipant?.isSpeaking == true
            ? 'YOU SPEAKING'
            : session.agent.agentState == sdk.AgentState.speaking
                ? 'AI SPEAKING' : 'LISTENING';""",
        """    final agentJoined = room.agentParticipant != null;
    if (_lastAgentJoined != agentJoined) {
      _lastAgentJoined = agentJoined;
      if (agentJoined &&
          connectionError?.startsWith('Connected, but the voice agent is still joining') == true) {
        connectionError = null;
      }
      notifyListeners();
    }
    final state = session.connectionState != sdk.ConnectionState.connected
        ? 'DISCONNECTED'
        : room.agentParticipant == null
            ? 'WAITING FOR BACY-10'
            : room.localParticipant?.isSpeaking == true
                ? 'YOU SPEAKING'
                : session.agent.agentState == sdk.AgentState.speaking
                    ? 'AI SPEAKING'
                    : session.agent.agentState == sdk.AgentState.thinking
                        ? 'THINKING' : 'LISTENING';""",
    )

    orb = mobile / "widgets/bacy_live_orb.dart"
    one(
        orb,
        """        final connected =
            session.connectionState == sdk.ConnectionState.connected;
        final userSpeaking = connected &&
            (room.localParticipant?.isSpeaking ?? false);
        final agentSpeaking =
            connected && session.agent.agentState == sdk.AgentState.speaking;
        final thinking =
            connected && session.agent.agentState == sdk.AgentState.thinking;""",
        """        final connected =
            session.connectionState == sdk.ConnectionState.connected;
        final agentReady = connected && room.agentParticipant != null;
        final userSpeaking = agentReady &&
            (room.localParticipant?.isSpeaking ?? false);
        final agentSpeaking =
            agentReady && session.agent.agentState == sdk.AgentState.speaking;
        final thinking =
            agentReady && session.agent.agentState == sdk.AgentState.thinking;""",
    )
    one(
        orb,
        """        final status = !connected
            ? 'STANDBY'
            : userSpeaking
                ? 'YOU ARE SPEAKING'
                : agentSpeaking
                    ? 'BACY-10 IS SPEAKING'
                    : thinking ? 'PROCESSING' : 'LISTENING';""",
        """        final status = !connected
            ? 'STANDBY'
            : !agentReady
                ? 'WAITING FOR BACY-10'
                : userSpeaking
                    ? 'YOU ARE SPEAKING'
                    : agentSpeaking
                        ? 'BACY-10 IS SPEAKING'
                        : thinking ? 'PROCESSING' : 'LISTENING';""",
    )
    one(
        orb,
        """        final energy = userSpeaking
            ? (0.60 + level * 1.30).clamp(0.0, 1.8).toDouble()
            : agentSpeaking
                ? (0.67 + agentLevel * 1.15).clamp(0.0, 1.8).toDouble()
                : thinking ? .43 : connected ? .22 : .12;""",
        """        final energy = !agentReady
            ? .12
            : userSpeaking
                ? (0.60 + level * 1.30).clamp(0.0, 1.8).toDouble()
                : agentSpeaking
                    ? (0.67 + agentLevel * 1.15).clamp(0.0, 1.8).toDouble()
                    : thinking ? .43 : .22;""",
    )

    screen = mobile / "screens/agent_screen.dart"
    one(
        screen,
        """              const Positioned.fill(child: BacyResultsPanel()),
              Positioned(""",
        """              const Positioned.fill(child: BacyResultsPanel()),
              Positioned(
                left: 16, right: 16, top: 62,
                child: Consumer<AppCtrl>(
                  builder: (context, ctrl, _) {
                    final message = ctrl.connectionError;
                    if (message == null || message.isEmpty) {
                      return const SizedBox.shrink();
                    }
                    return Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      decoration: BoxDecoration(
                        color: const Color(0xE6171D29),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFF725C54)),
                      ),
                      child: Text(message, textAlign: TextAlign.center,
                        style: const TextStyle(color: Color(0xFFE6C7BD), fontSize: 12)),
                    );
                  },
                ),
              ),
              Positioned(""",
    )
    one(
        screen,
        """                    if (session.connectionState != sdk.ConnectionState.disconnected
                        || ctrl.isSessionStarting) {
                      return const SizedBox.shrink();
                    }
                    return Center(child: ConstrainedBox(""",
        """                    final waitingForAgent =
                        session.connectionState == sdk.ConnectionState.connected &&
                        ctrl.room.agentParticipant == null;
                    if ((!waitingForAgent &&
                            session.connectionState != sdk.ConnectionState.disconnected) ||
                        ctrl.isSessionStarting) {
                      return const SizedBox.shrink();
                    }
                    return Center(child: ConstrainedBox(""",
    )
    one(
        screen,
        """                        onPressed: ctrl.connect,
                        icon: const Icon(Icons.refresh_rounded),
                        label: const Text('RECONNECT VOICE'),""",
        """                        onPressed: () {
                          if (waitingForAgent) {
                            ctrl.reconnectVoice();
                          } else {
                            ctrl.connect();
                          }
                        },
                        icon: const Icon(Icons.refresh_rounded),
                        label: Text(waitingForAgent ? 'RETRY VOICE AGENT' : 'RECONNECT VOICE'),""",
    )

    one(
        ctrl,
        """  Future<void> disconnect() async {""",
        """  Future<void> reconnectVoice() async {
    if (isSessionStarting) return;
    await disconnect();
    await Future<void>.delayed(const Duration(milliseconds: 350));
    connect();
  }

  Future<void> disconnect() async {""",
    )

    test = root / "agent/tests/test_v41_agent_presence.py"
    test.write_text(
        """from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def test_connected_room_is_not_mistaken_for_a_joined_agent():
    ctrl = (ROOT / 'mobile/lib/controllers/app_ctrl.dart').read_text()
    assert 'while (room.agentParticipant == null' in ctrl
    assert 'if (room.agentParticipant == null)' in ctrl
    assert 'room.remoteParticipants.isEmpty' not in ctrl
    assert 'Future<void> reconnectVoice() async' in ctrl
    assert 'LiveKit room connected without the BACY-10 agent' in ctrl

def test_orb_and_overlay_report_missing_agent_instead_of_listening():
    orb = (ROOT / 'mobile/lib/widgets/bacy_live_orb.dart').read_text()
    ctrl = (ROOT / 'mobile/lib/controllers/app_ctrl.dart').read_text()
    assert 'final agentReady = connected && room.agentParticipant != null;' in orb
    assert "'WAITING FOR BACY-10'" in orb
    assert "'WAITING FOR BACY-10'" in ctrl

def test_agent_screen_shows_error_and_offers_retry():
    screen = (ROOT / 'mobile/lib/screens/agent_screen.dart').read_text()
    assert 'ctrl.connectionError' in screen
    assert 'waitingForAgent' in screen
    assert 'RETRY VOICE AGENT' in screen
    assert 'ctrl.reconnectVoice()' in screen
""",
        encoding="utf-8",
    )
