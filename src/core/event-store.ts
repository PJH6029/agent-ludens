import { appendFile, readdir, writeFile } from 'node:fs/promises';

import { sessionEventSchema, sessionSummarySchema, type DoctorReport, type SessionDetail, type SessionEvent, type SessionSummary } from '../shared/contracts';
import { redactValue } from '../shared/redaction';
import { createId } from '../shared/ids';
import { readJsonIfExists, readTextIfExists, sessionEventFile, sessionLogFile, sessionSnapshotFile, writeJsonAtomic, type StoragePaths } from './storage';

export async function appendEvent(paths: StoragePaths, event: Omit<SessionEvent, 'id'>): Promise<SessionEvent> {
  const fullEvent = sessionEventSchema.parse({ ...event, id: createId('evt') });
  await appendFile(sessionEventFile(paths, fullEvent.sessionId), `${JSON.stringify(fullEvent)}\n`, 'utf8');
  return fullEvent;
}

export async function readEvents(paths: StoragePaths, sessionId: string, afterSequence = 0, limit = 200): Promise<SessionEvent[]> {
  const text = await readTextIfExists(sessionEventFile(paths, sessionId));
  if (!text) return [];
  const lines = text.split('\n').filter(Boolean);
  const events: SessionEvent[] = [];
  for (const line of lines) {
    try {
      const event = sessionEventSchema.parse(JSON.parse(line));
      if (event.sequence > afterSequence) {
        events.push(event);
      }
    } catch {
      // tolerate trailing partial lines
    }
  }
  return events.slice(-limit);
}

export async function lastSequence(paths: StoragePaths, sessionId: string): Promise<number> {
  const events = await readEvents(paths, sessionId, 0, 10_000);
  return events.at(-1)?.sequence ?? 0;
}

export async function writeSnapshot(paths: StoragePaths, detail: SessionDetail): Promise<void> {
  await writeJsonAtomic(sessionSnapshotFile(paths, detail.id), detail);
}

export async function readSnapshot(paths: StoragePaths, sessionId: string): Promise<SessionDetail | undefined> {
  return readJsonIfExists<SessionDetail>(sessionSnapshotFile(paths, sessionId));
}

export async function listSnapshots(paths: StoragePaths): Promise<SessionDetail[]> {
  const entries = await readdir(paths.sessionSnapshotsDir, { withFileTypes: true }).catch(() => []);
  const snapshots: SessionDetail[] = [];
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith('.json')) continue;
    const detail = await readJsonIfExists<SessionDetail>(sessionSnapshotFile(paths, entry.name.replace(/\.json$/, '')));
    if (detail) snapshots.push(detail);
  }
  return snapshots.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export async function writeActiveSessions(paths: StoragePaths, sessions: SessionSummary[]): Promise<void> {
  await writeJsonAtomic(paths.activeSessionsFile, { items: sessions.map((item) => sessionSummarySchema.parse(item)) });
}

export async function rebuildActiveSessions(paths: StoragePaths): Promise<SessionSummary[]> {
  const snapshots = await listSnapshots(paths);
  const items = snapshots
    .filter((snapshot) => snapshot.status !== 'terminated')
    .map((snapshot) => sessionSummarySchema.parse({
      id: snapshot.id,
      title: snapshot.title,
      agentId: snapshot.agentId,
      status: snapshot.status,
      mode: snapshot.mode,
      cwd: snapshot.cwd,
      hasPendingActions: snapshot.pendingActions.some((pending) => pending.status === 'open'),
      createdAt: snapshot.createdAt,
      updatedAt: snapshot.updatedAt,
      lastSequence: snapshot.lastSequence,
    }));
  await writeActiveSessions(paths, items);
  return items;
}

export async function persistDoctorReport(paths: StoragePaths, report: DoctorReport): Promise<void> {
  await writeJsonAtomic(paths.doctorFile, redactValue(report));
}

export async function appendDaemonLog(paths: StoragePaths, data: unknown): Promise<void> {
  await appendFile(paths.daemonLogFile, `${JSON.stringify(redactValue({ at: new Date().toISOString(), ...((data as Record<string, unknown>) || {}) }))}\n`, 'utf8');
}

export async function appendSessionLog(paths: StoragePaths, sessionId: string, data: unknown): Promise<void> {
  await appendFile(sessionLogFile(paths, sessionId), `${JSON.stringify(redactValue({ at: new Date().toISOString(), ...((data as Record<string, unknown>) || {}) }))}\n`, 'utf8');
}

export async function appendProbeLog(paths: StoragePaths, data: unknown): Promise<void> {
  await appendFile(paths.adapterProbeLogFile, `${JSON.stringify(redactValue({ at: new Date().toISOString(), ...((data as Record<string, unknown>) || {}) }))}\n`, 'utf8');
}

export async function writeDaemonRuntime(paths: StoragePaths, pid: number, url: string): Promise<void> {
  await writeFile(paths.daemonPidFile, `${pid}\n`, 'utf8');
  await writeFile(paths.daemonUrlFile, `${url}\n`, 'utf8');
}
