import assert from 'node:assert/strict'
import test from 'node:test'
import { domainChecks, domainState } from '../frontend/src/lib/domainPresentation.js'

const normalDns = { state: 'ok' }
const unknown = { state: 'unknown' }
const row = (checks, severity = 0) => ({ enabled: true, last_checked_at: '2026-11-23', checks, incident_level: severity })

test('unavailable registration does not affect a normal DNS result', () => {
  for (const state of ['unknown', 'unsupported']) {
    const domain = row({ delegation: normalDns, registration: { state }, expiry: { state } })
    assert.equal(domainState(domain).label, '正常')
    assert.deepEqual(domainChecks(domain).map(([key]) => key), ['delegation'])
  }
})

test('legacy registration coverage cannot hide a real DNS or registration fault', () => {
  const checks = { delegation: normalDns, registration: unknown, 'coverage:registration': { active: 1 } }
  assert.equal(domainState(row(checks, 1)).category, 'normal')
  const dnsFault = { ...checks, 'coverage:delegation': { active: 1 } }
  assert.equal(domainState(row(dnsFault, 1)).category, 'issues')
  const registrationFault = { ...checks, registration: { ...unknown, active: 2 } }
  assert.equal(domainState(row(registrationFault, 2)).label, '严重异常')
  assert(domainChecks(row(registrationFault)).some(([key]) => key === 'registration'))
})

test('missing DNS results stay pending and known expiry reminders are unchanged', () => {
  assert.equal(domainState(row({ delegation: unknown, registration: unknown })).label, '部分未确认')
  assert.equal(domainState(row({ delegation: normalDns, expiry: { state: 'bad' } })).label, '到期提醒')
})
