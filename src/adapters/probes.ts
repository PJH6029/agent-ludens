import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { ApiError } from '../shared/errors';
import type { AdapterCapability, AdapterProbeResult } from '../shared/contracts';
import type { AgentAdapter, AdapterSessionHandle } from './base';

const execFileAsync = promisify(execFile);

async function probeBinary(agentId: string, command: string, displayName: string): Promise<AdapterProbeResult> {
  try {
    const { stdout } = await execFileAsync('which', [command]);
    const binaryPath = stdout.trim() || null;
    const version = binaryPath ? (await execFileAsync(command, ['--version']).catch(() => ({ stdout: '' }))).stdout.trim() || null : null;
    return {
      agentId,
      installed: Boolean(binaryPath),
      binaryPath,
      version,
      authenticated: null,
      tmuxAvailable: true,
      status: binaryPath ? 'warning' : 'blocked',
      summary: binaryPath ? `${displayName} detected, but runtime integration is currently probe-only.` : `${displayName} binary is not installed.`,
      details: binaryPath
        ? ['Probe/capability reporting is available.', 'Interactive session runtime is not fully implemented yet.']
        : [`Install ${command} to enable this adapter.`],
    };
  } catch {
    return {
      agentId,
      installed: false,
      binaryPath: null,
      version: null,
      authenticated: null,
      tmuxAvailable: true,
      status: 'blocked',
      summary: `${displayName} binary is not installed.`,
      details: [`Install ${command} to enable this adapter.`],
    };
  }
}

class ProbeOnlyAdapter implements AgentAdapter {
  constructor(
    readonly id: string,
    readonly displayName: string,
    private readonly command: string,
    private readonly capabilityValue: AdapterCapability,
  ) {}

  capability(): AdapterCapability {
    return this.capabilityValue;
  }

  probe(): Promise<AdapterProbeResult> {
    return probeBinary(this.id, this.command, this.displayName);
  }

  async optionSchema(): Promise<Record<string, unknown>> {
    return {
      schema: { type: 'object', properties: {} },
      ui: {},
      defaults: {},
    };
  }

  async createSession(): Promise<AdapterSessionHandle> {
    throw new ApiError(409, 'adapter_not_available', `${this.displayName} session runtime is not implemented yet. Use the fake adapter for local workflows.`, { agentId: this.id });
  }
}

export function createBuiltInAdapters(): AgentAdapter[] {
  return [
    new ProbeOnlyAdapter('codex', 'Codex', 'codex', {
      agentId: 'codex',
      displayName: 'Codex',
      transport: 'pty',
      supportsPlanMode: true,
      supportsModeSwitch: true,
      supportsExecutionPolicySwitch: true,
      supportsPendingApprovals: true,
      supportsQuestions: true,
      supportsTmuxAttach: true,
      supportsStructuredEvents: true,
      supportsResume: true,
      supportsForceTerminate: true,
      supportsLocalBrowserOpen: false,
      planModeImplementation: 'native',
      executionPolicyImplementation: 'native',
      notes: ['Probe-only runtime in this initial slice.', 'Target integration surfaces: per-session config overrides, native plan/sandbox mapping, notify hook, session history relay.'],
    }),
    new ProbeOnlyAdapter('claude', 'Claude Code', 'claude', {
      agentId: 'claude',
      displayName: 'Claude Code',
      transport: 'pty',
      supportsPlanMode: true,
      supportsModeSwitch: true,
      supportsExecutionPolicySwitch: true,
      supportsPendingApprovals: true,
      supportsQuestions: true,
      supportsTmuxAttach: true,
      supportsStructuredEvents: true,
      supportsResume: true,
      supportsForceTerminate: true,
      supportsLocalBrowserOpen: false,
      planModeImplementation: 'emulated',
      executionPolicyImplementation: 'adapter_enforced',
      notes: ['Probe-only runtime in this initial slice.', 'Target integration surfaces: official hooks, emulated plan mode, structured question injection.'],
    }),
    new ProbeOnlyAdapter('opencode', 'OpenCode', 'opencode', {
      agentId: 'opencode',
      displayName: 'OpenCode',
      transport: 'http',
      supportsPlanMode: true,
      supportsModeSwitch: true,
      supportsExecutionPolicySwitch: true,
      supportsPendingApprovals: true,
      supportsQuestions: false,
      supportsTmuxAttach: false,
      supportsStructuredEvents: true,
      supportsResume: true,
      supportsForceTerminate: true,
      supportsLocalBrowserOpen: false,
      planModeImplementation: 'native',
      executionPolicyImplementation: 'limited',
      notes: ['Probe-only runtime in this initial slice.', 'Target integration surfaces: official server transport, build/plan mapping, honest permissions reporting.'],
    }),
  ];
}
