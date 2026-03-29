import { describe, expect, it } from 'vitest';

import { redactValue } from '../../src/shared/redaction';

describe('redactValue', () => {
  it('redacts nested secret-like keys', () => {
    const result = redactValue({ token: 'abc', nested: { password: 'secret', ok: true } });
    expect(result).toEqual({ token: '[redacted]', nested: { password: '[redacted]', ok: true } });
  });
});
