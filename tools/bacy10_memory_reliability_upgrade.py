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

  static Future<bool> flushFacts() async {
    if (_factFlushing) return false;
    if (!await _completePendingReset()) return false;
    _factFlushing = true;
    var acknowledged = true;
    try {
      final epoch = await _ensureEpoch() ?? 'bacy-initial';
      final unsynced = await pendingFacts();
      // Bounded retries: keep a long offline queue, don't block opening the app.
      for (final entry in unsynced.entries.take(12)) {
        final response = await request('POST', '/memory/fact', {
          'key': entry.key,
          'value': entry.value,
          'memory_epoch': epoch,
          'allow_readd': true,
        });
        if (response?.statusCode != 200) {
          acknowledged = false;
          break;
        }
        try {
          final payload = jsonDecode(response!.body);
          if (payload is Map && payload['ignored'] != null) acknowledged = false;
        } catch (_) { acknowledged = false; }
        final latest = await pendingFacts();
        // Don't erase a newer edit made while the previous one was in flight.
        if (latest[entry.key] == entry.value) {
          latest.remove(entry.key);
          await _storage.write(key: _factQueueKey, value: jsonEncode(latest));
        }
      }
      return acknowledged && (await pendingFacts()).isEmpty;
    } finally {
      _factFlushing = false;
    }
  }

  static Future<bool> remember(String key, String value) async {
    // Persist the pending operation before attempting the network.
    final pending = await pendingFacts();
    pending[key] = value;
    await _storage.write(key: _factQueueKey, value: jsonEncode(pending));
    final synced = await flushFacts();
    return synced && !(await pendingFacts()).containsKey(key);
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
    final online=await BacyCloudMemory.fetch();
    var local=await _local();
    if (online?['epochChanged'] == true) {
      local=<String,String>{};
      await saveAll(local);
    }
    await BacyCloudMemory.flushFacts();""")

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
      'Removed '+key+' on this phone. Cloud deletion is not yet confirmed; keep the app installed until it syncs.';""")

    once(memory, """    return synced ? 'Saved '+key+' in your private cloud memory.' :
      'Saved '+key+' on the phone; cloud sync is pending.';""", """    return synced ? 'Saved '+key+' in your private cloud memory. It can be restored after reinstall and re-pairing.' :
      'Saved '+key+' on this phone; cloud sync is not yet confirmed. Keep the app installed until it syncs.';""")

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

def test_secret_filter_and_durable_reset():
    cloud = (ROOT / "bacy10_cloud_memory.dart").read_text()
    memory = (ROOT / "bacy10_memory.dart").read_text()
    assert "containsSecret(String value)" in cloud
    assert "_luhnValid(String raw)" in cloud
    assert "containsSecret(key+' '+item)" in memory
    assert "_resetKey" in cloud
    assert "_epochKey" in cloud
    assert "_ensureEpoch" in cloud
    assert "memory_epoch" in cloud
    assert "epochChanged" in cloud
    assert "_completePendingReset" in cloud
    assert "await _storage.write(key: _resetKey, value: 'yes')" in cloud
''', encoding="utf-8")

def test_explicit_fact_readd_uses_current_epoch():
    cloud = (ROOT / "bacy10_cloud_memory.dart").read_text()
    worker = (ROOT.parents[2] / "cloud/bacy10-memory-worker.mjs").read_text()
    assert "'memory_epoch': epoch" in cloud
    assert "'allow_readd': true" in cloud
    assert "stale_memory_epoch" in worker
    assert "x.allow_readd!==true" in worker
