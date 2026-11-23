"""BACY-10 v3.1: private cloud fact recovery and reliable offline sync.

Applied to the original Android client after the v2.8 cloud memory upgrade.
No Cloudflare/LiveKit production service is modified by this patch.
"""
from pathlib import Path


def once(path: Path, original: str, replacement: str) -> None:
    current = path.read_text(encoding="utf-8")
    count = current.count(original)
    if count != 1:
        raise RuntimeError(f"Memory reliability anchor ({count}) in {path}: {original[:75]!r}")
    path.write_text(current.replace(original, replacement, 1), encoding="utf-8")


def apply(root: Path) -> None:
    mobile = root / "mobile"
    cloud = mobile / "lib/support/bacy10_cloud_memory.dart"
    memory = mobile / "lib/support/bacy10_memory.dart"

    once(cloud, "  static const _queueKey = 'bacy10_pending_cloud_turns_v1';", """  static const _queueKey = 'bacy10_pending_cloud_turns_v1';
  // Fact changes survive a lost connection and are retried after reconnecting.
  static const _factQueueKey = 'bacy10_pending_cloud_facts_v1';
  static bool _factFlushing = false;""")

    once(cloud, """  static Future<bool> remember(String key, String value) async =>
      (await request('POST','/memory/fact',{'key':key,'value':value}))
          ?.statusCode == 200;

  static Future<bool> forget(String key) async =>
      (await request('DELETE','/memory/fact',{'key':key}))
          ?.statusCode == 200;""", """  static Future<Map<String, String>> pendingFacts() async {
    try {
      final saved = await _storage.read(key: _factQueueKey);
      final decoded = jsonDecode(saved ?? '{}');
      if (decoded is Map) {
        return decoded.map<String, String>(
            (k, v) => MapEntry(k.toString(), v.toString()));
      }
    } catch (_) {}
    return <String, String>{};
  }

  static Future<void> flushFacts() async {
    if (_factFlushing) return;
    if (!await _completePendingReset()) return;
    _factFlushing = true;
    try {
      final unsynced = await pendingFacts();
      // Bounded retries: keep a long offline queue, don't block opening the app.
      for (final entry in unsynced.entries.take(12)) {
        final response = await request(
            'POST', '/memory/fact', {'key': entry.key, 'value': entry.value});
        if (response?.statusCode != 200) break;
        final latest = await pendingFacts();
        // Don't erase a newer edit made while the previous one was in flight.
        if (latest[entry.key] == entry.value) {
          latest.remove(entry.key);
          await _storage.write(key: _factQueueKey, value: jsonEncode(latest));
        }
      }
    } finally {
      _factFlushing = false;
    }
  }

  static Future<bool> remember(String key, String value) async {
    // Persist the pending operation before attempting the network.
    final pending = await pendingFacts();
    pending[key] = value;
    await _storage.write(key: _factQueueKey, value: jsonEncode(pending));
    await flushFacts();
    // True only if the latest value was acknowledged by the cloud service.
    return !(await pendingFacts()).containsKey(key);
  }

  static Future<bool> forget(String key) async =>
      remember(key, '__BACY10_DELETED__');""")

    once(cloud, """  static Future<bool> clearAll() async =>
      (await request('DELETE','/memory'))?.statusCode == 200;""", """  static Future<bool> clearAll() async {
    // Queue the reset before attempting the network. Old remote data is not
    // fetched or replayed until the server confirms this reset.
    await _storage.write(key: _resetKey, value: 'yes');
    await _storage.delete(key: _factQueueKey);
    await _storage.delete(key: _queueKey);
    return _completePendingReset();
  }""")

    once(memory, """  static Future<Map<String,String>> readAll() async {
    final local=await _local();
    final online=await BacyCloudMemory.fetch();""", """  static Future<Map<String,String>> readAll() async {
    await BacyCloudMemory.flushFacts();
    final local=await _local();
    final online=await BacyCloudMemory.fetch();""")

    once(memory, """      local.addAll(remote);
      await saveAll(local);
    }
    local.removeWhere((k,v)=>v==_deleted);""", """      // Cloud is authoritative, except for newer unsynced phone edits.
      // A deletion marker is intentionally preserved in the cloud so it
      // remains deleted after reinstall, even for bundled default facts.
      local.addAll(remote);
      local.addAll(await BacyCloudMemory.pendingFacts());
      await saveAll(local);
    } else {
      local.addAll(await BacyCloudMemory.pendingFacts());
    }
    local.removeWhere((k,v)=>v==_deleted);""")

    once(memory, """    final deleted=await BacyCloudMemory.forget(key);
    return deleted ? 'Removed '+key+' from cloud memory.' :
      'Removed '+key+' locally; cloud deletion needs internet.';""", """    // Store a cloud tombstone, not an ordinary DELETE. Otherwise built-in
    // default facts can reappear after the app is reinstalled.
    final deleted=await BacyCloudMemory.forget(key);
    return deleted ? 'Removed '+key+' from private cloud memory.' :
      'Removed '+key+' on this phone. Cloud deletion is queued; do not uninstall until it syncs.';""")

    once(memory, """    return synced ? 'Saved '+key+' in your private cloud memory.' :
      'Saved '+key+' on the phone; cloud sync is pending.';""", """    return synced ? 'Saved '+key+' in your private cloud memory. It can be restored after reinstall and re-pairing.' :
      'Saved '+key+' locally. Cloud backup is pending; do not uninstall until the cloud confirms it.';""")

    once(mobile / "pubspec.yaml", "version: 2.8.0+32", "version: 3.2.0+37")


    (root / "agent/tests/test_memory_reliability.py").write_text('''from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "mobile/lib/support"


def test_offline_memory_persists_until_cloud_ack():
    src = (ROOT / "bacy10_cloud_memory.dart").read_text()
    assert "_factQueueKey" in src
    assert "await flushFacts();" in src
    assert "_storage.write(key: _factQueueKey" in src
    assert "response?.statusCode != 200" in src
    assert "return !(await pendingFacts()).containsKey(key);" in src


def test_cloud_reinstall_and_deleted_defaults():
    src = (ROOT / "bacy10_memory.dart").read_text()
    assert "await BacyCloudMemory.flushFacts();" in src
    assert "local.addAll(remote);" in src
    assert "local.addAll(await BacyCloudMemory.pendingFacts());" in src
    assert "BacyCloudMemory.forget(key)" in src
    assert "cloud confirms" in src
    cloud = (ROOT / "bacy10_cloud_memory.dart").read_text()
    assert "remember(key, '__BACY10_DELETED__')" in cloud
''', encoding="utf-8")
