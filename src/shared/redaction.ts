const SECRET_KEYS = ['token', 'secret', 'password', 'authorization', 'cookie', 'apiKey', 'passwordHash'];

export function redactValue<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => redactValue(item)) as T;
  }

  if (value && typeof value === 'object') {
    const output: Record<string, unknown> = {};
    for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
      if (SECRET_KEYS.some((secretKey) => key.toLowerCase().includes(secretKey.toLowerCase()))) {
        output[key] = '[redacted]';
      } else {
        output[key] = redactValue(entry);
      }
    }
    return output as T;
  }

  return value;
}
