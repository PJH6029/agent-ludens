import { customAlphabet } from 'nanoid';

const alphabet = customAlphabet('0123456789abcdefghijklmnopqrstuvwxyz', 20);

export function createId(prefix: string): string {
  return `${prefix}_${alphabet()}`;
}
