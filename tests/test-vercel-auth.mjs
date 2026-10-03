import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createBrowserSession, requestOwner } from '../lib/runtime-config.ts';

process.env.SESSION_SECRET = 'test-only-session-secret-with-at-least-32-characters';
const request = cookie => new Request('https://example.com/api/matches', { headers: cookie ? { cookie } : {} });

test('new browsers have distinct signed owners and secure cookies', () => {
  const a = createBrowserSession(request());
  const b = createBrowserSession(request());
  assert.notEqual(a.owner, b.owner);
  assert.equal(requestOwner(request(a.cookie)), a.owner);
  assert.equal(requestOwner(request(b.cookie)), b.owner);
  for (const flag of ['HttpOnly', 'Secure', 'SameSite=Lax', 'Path=/']) assert.ok(a.cookie.includes(flag));
});
test('shared owner configuration and forged identity headers grant no access', () => {
  process.env.APP_OWNER_ID = 'previous-owner-must-not-be-used';
  assert.equal(requestOwner(new Request('https://example.com/api/matches', {
    headers: { 'oai-authenticated-user-id': 'attacker', 'x-vercel-authenticated-user': 'attacker' },
  })), null);
  delete process.env.APP_OWNER_ID;
});
test('modified signatures, payloads and malformed sessions are rejected', () => {
  const { cookie } = createBrowserSession(request());
  const token = cookie.split(';')[0];
  assert.equal(requestOwner(request(token.slice(0, -1) + (token.endsWith('a') ? 'b' : 'a'))), null);
  assert.equal(requestOwner(request(token.replace('=', '=x'))), null);
  for (const token of ['garbage', 'a.b.c', '.missing', 'missing.', 'x'.repeat(601)]) {
    assert.equal(requestOwner(request(`touchline_session=${token}`)), null);
  }
});
test('expired signed sessions are rejected', () => {
  const original = Date.now;
  try {
    Date.now = () => original() - 366 * 24 * 60 * 60 * 1000;
    const { cookie } = createBrowserSession(request());
    Date.now = original;
    assert.equal(requestOwner(request(cookie)), null);
  } finally { Date.now = original; }
});
test('missing signing configuration fails closed', () => {
  const previous = process.env.SESSION_SECRET;
  delete process.env.SESSION_SECRET;
  try { assert.throws(() => createBrowserSession(request()), /not configured/); }
  finally { process.env.SESSION_SECRET = previous; }
});
