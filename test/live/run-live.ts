import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

async function hasBinary(command: string) {
  try {
    const { stdout } = await execFileAsync('which', [command]);
    return Boolean(stdout.trim());
  } catch {
    return false;
  }
}

async function main() {
  const agentIndex = process.argv.findIndex((value) => value === '--agent');
  const agent = agentIndex >= 0 ? process.argv[agentIndex + 1] : undefined;
  if (!agent) {
    console.error('Usage: npm run test:live -- --agent <codex|claude|opencode>');
    process.exit(1);
  }

  const binary = agent === 'codex' ? 'codex' : agent === 'claude' ? 'claude' : agent === 'opencode' ? 'opencode' : undefined;
  if (!binary || !(await hasBinary(binary))) {
    console.error(`${agent} is not installed; live test is blocked.`);
    process.exit(2);
  }

  console.error(`${agent} binary is installed, but the live adapter flow is not implemented in this initial slice.`);
  process.exit(2);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
