import assert from 'node:assert/strict';
import { test } from 'node:test';
import { requestOwner } from '../lib/runtime-config.ts';

test('Vercel ignores a forged Sites identity and requires configured owner', () => {
  const previous = { VERCEL: process.env.VERCEL, APP_OWNER_ID: process.env.APP_OWNER_ID };
  try {
    process.env.VERCEL = '1';
    delete process.env.APP_OWNER_ID;
    const request = new Request('https://example.com/api/matches', {
      headers: { 'oai-authenticated-user-id': 'attacker' },
    });
    assert.equal(requestOwner(request), null);
    process.env.APP_OWNER_ID = 'configured-owner';
    assert.equal(requestOwner(request), 'configured-owner');
    delete process.env.VERCEL;
    assert.equal(requestOwner(request), null);
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
});
