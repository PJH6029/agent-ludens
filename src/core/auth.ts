import type { FastifyReply, FastifyRequest } from 'fastify';

import { authSessionSchema, type AppConfig } from '../shared/contracts';
import { ApiError } from '../shared/errors';
import { createId } from '../shared/ids';
import { hashPassword } from './config';

const SESSION_COOKIE = 'rcaio_session';
const CSRF_COOKIE = 'rcaio_csrf';

interface AuthRecord {
  token: string;
  csrfToken: string;
  createdAt: string;
}

export class AuthManager {
  private config: AppConfig;
  private readonly sessions = new Map<string, AuthRecord>();

  constructor(config: AppConfig) {
    this.config = config;
  }

  updateConfig(config: AppConfig): void {
    this.config = config;
  }

  async getBrowserAuthState(request: FastifyRequest, reply: FastifyReply) {
    if (this.config.server.authMode === 'local-session') {
      const session = this.getOrCreateLocalSession(request, reply);
      return authSessionSchema.parse({ authenticated: true, mode: 'local-session', csrfToken: session.csrfToken });
    }

    const session = this.getExistingSession(request);
    return authSessionSchema.parse({
      authenticated: Boolean(session),
      mode: 'password',
      csrfToken: session?.csrfToken,
    });
  }

  async login(password: string, reply: FastifyReply) {
    if (this.config.server.authMode !== 'password') {
      throw new ApiError(400, 'invalid_request', 'Password login is only available when auth mode is password.');
    }
    if (!this.config.server.passwordHash || hashPassword(password) !== this.config.server.passwordHash) {
      throw new ApiError(401, 'unauthorized', 'Invalid password.');
    }
    const session = this.issueSession(reply);
    return authSessionSchema.parse({ authenticated: true, mode: 'password', csrfToken: session.csrfToken });
  }

  async logout(request: FastifyRequest, reply: FastifyReply) {
    const token = request.cookies[SESSION_COOKIE];
    if (token) {
      this.sessions.delete(token);
    }
    reply.clearCookie(SESSION_COOKIE, { path: '/' });
    reply.clearCookie(CSRF_COOKIE, { path: '/' });
    return authSessionSchema.parse({ authenticated: false, mode: this.config.server.authMode });
  }

  isAuthenticated(request: FastifyRequest): boolean {
    if (this.config.server.authMode === 'local-session') {
      return Boolean(request.cookies[SESSION_COOKIE]);
    }
    return Boolean(this.getExistingSession(request));
  }

  requireAuth(request: FastifyRequest, reply: FastifyReply, options: { stateChanging?: boolean } = {}): AuthRecord {
    const session = this.config.server.authMode === 'local-session'
      ? this.getOrCreateLocalSession(request, reply)
      : this.getExistingSession(request);

    if (!session) {
      throw new ApiError(401, 'unauthorized', 'Authentication is required.');
    }

    if (options.stateChanging) {
      const headerToken = request.headers['x-csrf-token'];
      const cookieToken = request.cookies[CSRF_COOKIE];
      if (!headerToken || headerToken !== session.csrfToken || cookieToken !== session.csrfToken) {
        throw new ApiError(403, 'forbidden', 'Missing or invalid CSRF token.');
      }
    }

    return session;
  }

  private getExistingSession(request: FastifyRequest): AuthRecord | undefined {
    const token = request.cookies[SESSION_COOKIE];
    return token ? this.sessions.get(token) : undefined;
  }

  private getOrCreateLocalSession(request: FastifyRequest, reply: FastifyReply): AuthRecord {
    const existing = this.getExistingSession(request);
    if (existing) return existing;
    return this.issueSession(reply);
  }

  private issueSession(reply: FastifyReply): AuthRecord {
    const session: AuthRecord = {
      token: createId('auth'),
      csrfToken: createId('csrf'),
      createdAt: new Date().toISOString(),
    };
    this.sessions.set(session.token, session);
    reply.setCookie(SESSION_COOKIE, session.token, { httpOnly: true, sameSite: 'lax', path: '/' });
    reply.setCookie(CSRF_COOKIE, session.csrfToken, { httpOnly: false, sameSite: 'lax', path: '/' });
    return session;
  }
}
