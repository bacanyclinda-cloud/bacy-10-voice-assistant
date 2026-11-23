import test from "node:test";
import assert from "node:assert/strict";
import { isSensitiveMemoryContent } from "./bacy10-memory-worker.mjs";

test("blocks passwords and secret phrases", () => {
  assert.equal(isSensitiveMemoryContent("my API key is hidden"), true);
  assert.equal(isSensitiveMemoryContent("the one time password is 123456"), true);
});

test("blocks common API tokens, bearer tokens and JWTs", () => {
  assert.equal(isSensitiveMemoryContent("sk-" + "a".repeat(30)), true);
  assert.equal(isSensitiveMemoryContent("ghp_" + "a".repeat(35)), true);
  assert.equal(isSensitiveMemoryContent("Bearer " + "a".repeat(32)), true);
  assert.equal(isSensitiveMemoryContent("eyJ" + "a".repeat(20) + "." + "b".repeat(20) + "." + "c".repeat(20)), true);
});

test("blocks private keys and valid payment card numbers", () => {
  assert.equal(isSensitiveMemoryContent("-----BEGIN PRIVATE KEY-----"), true);
  assert.equal(isSensitiveMemoryContent("4111 1111 1111 1111"), true);
});

test("allows ordinary useful memory", () => {
  assert.equal(isSensitiveMemoryContent("I prefer a natural British voice."), false);
  assert.equal(isSensitiveMemoryContent("My project is called Bacy 10."), false);
});
