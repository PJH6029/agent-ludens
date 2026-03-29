import type { AgentAdapter, AdapterSessionHandle } from '../adapters/base';
import { FakeAdapter } from '../adapters/fake';
import { createBuiltInAdapters } from '../adapters/probes';
import {
  createSessionSchema,
  executionPolicySchema,
  type AppConfig,
  type CreateSessionInput,
  type ExecutionPolicy,
  type PendingAction,
  type SessionDetail,
  type SessionEvent,
  type SessionSummary,
} from '../shared/contracts';
import { ApiError } from '../shared/errors';
import { createId } from '../shared/ids';
import { appendDaemonLog, appendEvent, appendSessionLog, lastSequence, readEvents, rebuildActiveSessions, listSnapshots, writeActiveSessions, writeSnapshot } from './event-store';
import type { StoragePaths } from './storage';

interface RuntimeSession {
  detail: SessionDetail;
  adapter: AgentAdapter;
  handle?: AdapterSessionHandle;
}

type Subscriber = (event: SessionEvent) => void;

class EventBus {
  private readonly subscribers = new Set<Subscriber>();

  subscribe(listener: Subscriber): () => void {
    this.subscribers.add(listener);
    return () => this.subscribers.delete(listener);
  }

  publish(event: SessionEvent): void {
    for (const subscriber of this.subscribers) subscriber(event);
  }
}

function deriveTitle(initialPrompt: string): string {
  return initialPrompt.trim().slice(0, 72) || 'Untitled session';
}

function toSummary(detail: SessionDetail): SessionSummary {
  return {
    id: detail.id,
    title: detail.title,
    agentId: detail.agentId,
    status: detail.status,
    mode: detail.mode,
    cwd: detail.cwd,
    hasPendingActions: detail.pendingActions.some((pending) => pending.status === 'open'),
    createdAt: detail.createdAt,
    updatedAt: detail.updatedAt,
    lastSequence: detail.lastSequence,
  };
}

export class SessionManager {
  private readonly adapters = new Map<string, AgentAdapter>();
  private readonly sessions = new Map<string, RuntimeSession>();
  private readonly bus = new EventBus();

  constructor(private readonly config: AppConfig, private readonly paths: StoragePaths) {
    const allAdapters = [new FakeAdapter(), ...createBuiltInAdapters()];
    for (const adapter of allAdapters) this.adapters.set(adapter.id, adapter);
  }

  async initialize(): Promise<void> {
    const snapshots = await listSnapshots(this.paths);
    for (const snapshot of snapshots) {
      const adapter = this.getAdapter(snapshot.agentId);
      this.sessions.set(snapshot.id, { detail: snapshot, adapter });
    }
    await rebuildActiveSessions(this.paths);
  }

  listAdapters(): AgentAdapter[] {
    return [...this.adapters.values()];
  }

  subscribe(listener: Subscriber): () => void {
    return this.bus.subscribe(listener);
  }

  async listSessions(): Promise<SessionSummary[]> {
    return [...this.sessions.values()].map(({ detail }) => toSummary(detail)).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  getSession(sessionId: string): SessionDetail {
    const session = this.sessions.get(sessionId);
    if (!session) throw new ApiError(404, 'session_not_found', 'Session was not found.');
    return session.detail;
  }

  async getEvents(sessionId: string, afterSequence = 0, limit = this.config.ui.eventPageSize): Promise<SessionEvent[]> {
    return readEvents(this.paths, sessionId, afterSequence, limit);
  }

  async createSession(input: CreateSessionInput): Promise<SessionDetail> {
    const parsed = createSessionSchema.parse(input);
    const adapter = this.getAdapter(parsed.agentId);
    const now = new Date().toISOString();
    const detail: SessionDetail = {
      id: createId('ses'),
      title: parsed.title || deriveTitle(parsed.initialPrompt),
      agentId: parsed.agentId,
      status: 'starting',
      mode: parsed.mode,
      cwd: parsed.cwd,
      hasPendingActions: false,
      executionPolicy: executionPolicySchema.parse(parsed.executionPolicy),
      capabilities: adapter.capability(),
      pendingActions: [],
      createdAt: now,
      updatedAt: now,
      lastSequence: 0,
    };

    this.sessions.set(detail.id, { detail, adapter });
    await writeSnapshot(this.paths, detail);
    await this.syncActiveSessions();
    await this.recordEvent(detail.id, { type: 'session.started', source: { adapterId: adapter.id, vendorEventType: 'session.started' }, data: { cwd: detail.cwd } });
    await this.recordEvent(detail.id, { type: 'user.sent', source: { adapterId: adapter.id, vendorEventType: 'user.initial' }, data: { text: parsed.initialPrompt, clientMessageId: createId('msg') } });

    try {
      const handle = await adapter.createSession(parsed, {
        session: this.getSession(detail.id),
        emit: async (event) => {
          await this.recordEvent(detail.id, event);
        },
      });
      this.sessions.get(detail.id)!.handle = handle;
      return this.getSession(detail.id);
    } catch (error) {
      await this.recordEvent(detail.id, {
        type: 'session.error',
        source: { adapterId: adapter.id, vendorEventType: 'adapter.create.error' },
        data: { code: 'adapter_launch_failed', message: error instanceof Error ? error.message : 'Failed to create session.', recoverable: true, actionHint: 'Review doctor output and retry.' },
      });
      throw error;
    }
  }

  async sendMessage(sessionId: string, input: { text: string; clientMessageId: string }): Promise<SessionDetail> {
    const session = this.requireRuntimeSession(sessionId);
    await this.recordEvent(sessionId, { type: 'user.sent', source: { adapterId: session.adapter.id, vendorEventType: 'user.sent' }, data: input });
    await session.handle!.sendMessage(input);
    return this.getSession(sessionId);
  }

  async updateMode(sessionId: string, mode: 'build' | 'plan'): Promise<{ mode: 'build' | 'plan'; restartRequired: boolean }> {
    const session = this.requireRuntimeSession(sessionId);
    const result = await session.handle!.setMode(mode);
    await this.recordEvent(sessionId, {
      type: 'session.updated',
      source: { adapterId: session.adapter.id, vendorEventType: 'mode.updated' },
      data: { mode, restartRequired: result.restartRequired, status: result.restartRequired ? 'restarting' : 'idle' },
    });
    return { mode, restartRequired: result.restartRequired };
  }

  async updatePolicy(sessionId: string, executionPolicy: ExecutionPolicy): Promise<{ executionPolicy: ExecutionPolicy; restartRequired: boolean }> {
    const session = this.requireRuntimeSession(sessionId);
    const normalized = executionPolicySchema.parse(executionPolicy);
    const result = await session.handle!.updateExecutionPolicy(normalized);
    await this.recordEvent(sessionId, {
      type: 'session.updated',
      source: { adapterId: session.adapter.id, vendorEventType: 'policy.updated' },
      data: { executionPolicy: normalized, restartRequired: result.restartRequired },
    });
    return { executionPolicy: normalized, restartRequired: result.restartRequired };
  }

  async resolvePending(sessionId: string, pendingId: string, resolution: { optionId: string; text?: string }): Promise<void> {
    const session = this.requireRuntimeSession(sessionId);
    const pending = session.detail.pendingActions.find((item) => item.id === pendingId && item.status === 'open');
    if (!pending) throw new ApiError(404, 'pending_action_not_found', 'Pending action was not found.');
    const eventType = pending.type === 'approval' ? 'approval.resolved' : pending.type === 'question' ? 'question.resolved' : 'plan.resolved';
    await this.recordEvent(sessionId, {
      type: eventType,
      source: { adapterId: session.adapter.id, vendorEventType: 'pending.resolved' },
      data: { pendingId, resolution },
    });
    await session.handle!.resolvePending(pending, resolution);
  }

  async terminate(sessionId: string, force = false): Promise<void> {
    const session = this.requireRuntimeSession(sessionId);
    await session.handle!.terminate(force);
    await this.recordEvent(sessionId, {
      type: 'session.terminated',
      source: { adapterId: session.adapter.id, vendorEventType: 'session.terminated' },
      data: { force },
    });
    delete session.handle;
  }

  private getAdapter(agentId: string): AgentAdapter {
    const adapter = this.adapters.get(agentId);
    if (!adapter) throw new ApiError(409, 'adapter_not_available', `Adapter ${agentId} is not available.`);
    return adapter;
  }

  private requireRuntimeSession(sessionId: string): RuntimeSession {
    const session = this.sessions.get(sessionId);
    if (!session) throw new ApiError(404, 'session_not_found', 'Session was not found.');
    if (!session.handle) throw new ApiError(409, 'conflict', 'Session runtime is not active for this action.');
    return session;
  }

  private async recordEvent(sessionId: string, event: Omit<SessionEvent, 'id' | 'sessionId' | 'sequence' | 'createdAt'>): Promise<SessionEvent> {
    const runtime = this.sessions.get(sessionId);
    if (!runtime) throw new ApiError(404, 'session_not_found', 'Session was not found.');
    const sequence = (await lastSequence(this.paths, sessionId)) + 1;
    const stored = await appendEvent(this.paths, {
      sessionId,
      sequence,
      createdAt: new Date().toISOString(),
      ...event,
    });
    runtime.detail = this.applyEvent(runtime.detail, stored);
    this.sessions.set(sessionId, runtime);
    await writeSnapshot(this.paths, runtime.detail);
    await this.syncActiveSessions();
    await appendSessionLog(this.paths, sessionId, stored);
    this.bus.publish(stored);
    await appendDaemonLog(this.paths, { scope: 'session-event', sessionId, type: stored.type });
    return stored;
  }

  private applyEvent(detail: SessionDetail, event: SessionEvent): SessionDetail {
    const next: SessionDetail = {
      ...detail,
      pendingActions: [...detail.pendingActions],
      lastSequence: event.sequence,
      updatedAt: event.createdAt,
    };

    switch (event.type) {
      case 'session.started':
        next.status = 'idle';
        break;
      case 'user.sent':
        next.status = 'running';
        break;
      case 'approval.requested':
      case 'question.requested':
      case 'plan.requested': {
        const pending = event.data.pendingAction as PendingAction;
        next.pendingActions = [...next.pendingActions, pending];
        next.status = event.type === 'approval.requested' ? 'waiting_approval' : event.type === 'question.requested' ? 'waiting_question' : 'waiting_plan';
        break;
      }
      case 'approval.resolved':
      case 'question.resolved':
      case 'plan.resolved': {
        const pendingId = event.data.pendingId as string;
        next.pendingActions = next.pendingActions.map((pending) => pending.id === pendingId ? { ...pending, status: 'resolved' } : pending);
        next.status = 'running';
        break;
      }
      case 'assistant.final':
        if (!next.pendingActions.some((pending) => pending.status === 'open')) {
          next.status = 'idle';
        }
        break;
      case 'session.updated':
        if (event.data.mode === 'build' || event.data.mode === 'plan') next.mode = event.data.mode;
        if (event.data.executionPolicy) next.executionPolicy = executionPolicySchema.parse(event.data.executionPolicy);
        if (typeof event.data.status === 'string') next.status = event.data.status as SessionDetail['status'];
        break;
      case 'session.terminated':
        next.status = 'terminated';
        next.pendingActions = next.pendingActions.map((pending) => pending.status === 'open' ? { ...pending, status: 'invalidated' } : pending);
        break;
      case 'session.error':
        next.status = 'error';
        break;
      default:
        break;
    }

    next.hasPendingActions = next.pendingActions.some((pending) => pending.status === 'open');

    return next;
  }

  private async syncActiveSessions(): Promise<void> {
    const items = [...this.sessions.values()]
      .map(({ detail }) => detail)
      .filter((detail) => detail.status !== 'terminated')
      .map((detail) => toSummary(detail));
    await writeActiveSessions(this.paths, items);
  }
}
