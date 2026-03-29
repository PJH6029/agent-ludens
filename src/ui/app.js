const state = {
  auth: null,
  csrfToken: '',
  sessions: [],
  sessionDetails: new Map(),
  events: new Map(),
  doctor: null,
  settings: null,
  agents: [],
  socket: null,
};

const views = {
  login: document.querySelector('#login-view'),
  dashboard: document.querySelector('#dashboard-view'),
  workspace: document.querySelector('#workspace-view'),
  settings: document.querySelector('#settings-view'),
  doctor: document.querySelector('#doctor-view'),
};

async function api(path, init = {}) {
  const headers = new Headers(init.headers || {});
  if (init.body && !headers.has('content-type')) headers.set('content-type', 'application/json');
  if (init.method && init.method !== 'GET' && init.method !== 'HEAD' && state.csrfToken) headers.set('x-csrf-token', state.csrfToken);
  const response = await fetch(path, { ...init, headers });
  const json = await response.json();
  if (!response.ok) throw new Error(json.error?.message || `Request failed: ${response.status}`);
  return json.data;
}

function currentRoute() {
  const hash = location.hash || '#/dashboard';
  const [, route, maybeId] = hash.split('/');
  return { route: route || 'dashboard', id: maybeId };
}

function show(view) {
  Object.values(views).forEach((element) => element.classList.add('hidden'));
  views[view].classList.remove('hidden');
}

function formatEvent(event) {
  if (event.type === 'assistant.delta') return event.data.textDelta;
  if (event.type === 'assistant.final') return event.data.text;
  if (event.type === 'user.sent') return event.data.text;
  if (event.type === 'terminal.output') return event.data.chunk;
  if (event.type.endsWith('.requested')) return event.data.pendingAction?.prompt || event.type;
  if (event.type.endsWith('.resolved')) return JSON.stringify(event.data.resolution || {});
  return JSON.stringify(event.data);
}

function renderLogin() {
  show('login');
  views.login.innerHTML = `
    <h2>Login required</h2>
    <p class="muted">This daemon is configured for password authentication.</p>
    <form id="login-form" class="card">
      <label>Password <input type="password" name="password" required /></label>
      <button class="primary" type="submit">Login</button>
    </form>
  `;
  views.login.querySelector('#login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const password = new FormData(event.currentTarget).get('password');
    const data = await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ password }) });
    state.auth = data;
    state.csrfToken = data.csrfToken || '';
    await bootstrap();
  });
}

function renderDashboard() {
  show('dashboard');
  views.dashboard.innerHTML = `
    <div class="grid-2">
      <section class="card">
        <h2>Create session</h2>
        <form id="new-session-form">
          <label>Agent
            <select name="agentId">${state.agents.map((agent) => `<option value="${agent.probe.agentId}">${agent.capabilities.displayName} — ${agent.probe.status}</option>`).join('')}</select>
          </label>
          <label>Working directory <input name="cwd" value="${location.pathname}" required /></label>
          <label>Optional title <input name="title" /></label>
          <label>Initial prompt <textarea name="initialPrompt" rows="4" required>Inspect the repository and summarize the next steps.</textarea></label>
          <label>Mode
            <select name="mode"><option value="build">build</option><option value="plan">plan</option></select>
          </label>
          <button class="primary" type="submit">Create session</button>
        </form>
      </section>
      <section class="card">
        <h2>Daemon</h2>
        <p class="muted">Adapter readiness and doctor summary.</p>
        <div class="list">${state.agents.map((agent) => `
          <article class="card">
            <h3>${agent.capabilities.displayName}</h3>
            <p><span class="status-badge">${agent.probe.status}</span></p>
            <p>${agent.probe.summary}</p>
            <p class="muted">${(agent.probe.details || []).join(' • ')}</p>
          </article>
        `).join('')}</div>
      </section>
    </div>
    <section class="card">
      <h2>Recent sessions</h2>
      <div class="list">${state.sessions.map((session) => `
        <button class="card secondary" data-session-link="${session.id}">
          <h3>${session.title}</h3>
          <p>${session.agentId} · ${session.status} · ${session.mode}</p>
          <p class="muted">${session.cwd}</p>
        </button>
      `).join('') || '<p class="muted">No sessions yet.</p>'}</div>
    </section>
  `;

  views.dashboard.querySelectorAll('[data-session-link]').forEach((button) => {
    button.addEventListener('click', () => {
      location.hash = `#/session/${button.dataset.sessionLink}`;
    });
  });

  views.dashboard.querySelector('#new-session-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const detail = await api('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({
        agentId: formData.get('agentId'),
        cwd: formData.get('cwd'),
        title: formData.get('title') || '',
        initialPrompt: formData.get('initialPrompt'),
        mode: formData.get('mode'),
        executionPolicy: { filesystem: 'workspace-write', network: 'on', approvals: 'on-request', writableRoots: [] },
        extraDirectories: [],
        adapterOptions: {},
      }),
    });
    state.sessionDetails.set(detail.id, detail);
    await refreshSessions();
    location.hash = `#/session/${detail.id}`;
  });
}

function renderWorkspace(sessionId) {
  const detail = state.sessionDetails.get(sessionId);
  if (!detail) {
    location.hash = '#/dashboard';
    return;
  }
  show('workspace');
  const events = state.events.get(sessionId) || [];
  views.workspace.innerHTML = `
    <div class="workspace-grid">
      <section class="card">
        <h2>${detail.title}</h2>
        <p>${detail.agentId} · ${detail.status} · ${detail.mode}</p>
        <div class="transcript" aria-live="polite">${events.map((event) => `
          <article class="message">
            <div class="channel">${event.type}</div>
            <div>${formatEvent(event)}</div>
          </article>
        `).join('') || '<p class="muted">No transcript events yet.</p>'}</div>
        <form id="composer-form">
          <label>Message <textarea name="text" rows="3" required></textarea></label>
          <button class="primary" type="submit">Send</button>
        </form>
      </section>
      <aside class="card">
        <h3>Pending actions</h3>
        <div class="pending-actions">${detail.pendingActions.filter((pending) => pending.status === 'open').map((pending) => `
          <article class="card">
            <h4>${pending.type}</h4>
            <p>${pending.prompt}</p>
            ${pending.type === 'question' ? `<input data-answer-input="${pending.id}" placeholder="Enter answer" />` : ''}
            <div class="inline-actions">${pending.options.map((option) => `<button data-resolve="${pending.id}" data-option="${option.id}">${option.label}</button>`).join('')}</div>
          </article>
        `).join('') || '<p class="muted">No pending actions.</p>'}</div>
        <h3>Controls</h3>
        <div class="inline-actions">
          <button data-mode="build">Build mode</button>
          <button data-mode="plan">Plan mode</button>
          <button data-force="false" class="danger">Terminate</button>
          <button data-force="true" class="danger">Force terminate</button>
          <button data-attach="true">Attach</button>
        </div>
        <h3>Terminal</h3>
        <pre class="terminal">${events.filter((event) => event.type === 'terminal.output').map((event) => event.data.chunk).join('') || 'No terminal output.'}</pre>
      </aside>
    </div>
  `;

  views.workspace.querySelector('#composer-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = new FormData(event.currentTarget).get('text');
    await api(`/api/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ text, clientMessageId: `msg_${Date.now()}` }),
    });
    event.currentTarget.reset();
  });

  views.workspace.querySelectorAll('[data-resolve]').forEach((button) => {
    button.addEventListener('click', async () => {
      const pendingId = button.dataset.resolve;
      const optionId = button.dataset.option;
      const textInput = views.workspace.querySelector(`[data-answer-input="${pendingId}"]`);
      await api(`/api/sessions/${sessionId}/pending/${pendingId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ resolution: { optionId, text: textInput?.value || undefined } }),
      });
    });
  });

  views.workspace.querySelectorAll('[data-mode]').forEach((button) => {
    button.addEventListener('click', async () => {
      await api(`/api/sessions/${sessionId}/mode`, { method: 'POST', body: JSON.stringify({ mode: button.dataset.mode }) });
    });
  });

  views.workspace.querySelectorAll('[data-force]').forEach((button) => {
    button.addEventListener('click', async () => {
      await api(`/api/sessions/${sessionId}/terminate`, { method: 'POST', body: JSON.stringify({ force: button.dataset.force === 'true' }) });
      await refreshSessions();
    });
  });

  views.workspace.querySelector('[data-attach]').addEventListener('click', async () => {
    if (!detail.capabilities.supportsTmuxAttach) {
      alert('Attach is not supported for this session.');
      return;
    }
    alert('Attach is declared but not implemented in this initial slice.');
  });
}

function renderSettings() {
  show('settings');
  const settings = state.settings;
  views.settings.innerHTML = `
    <section class="card">
      <h2>Settings</h2>
      <form id="settings-form">
        <label>Host <input name="host" value="${settings.server.host}" /></label>
        <label>Port <input type="number" name="port" value="${settings.server.port}" /></label>
        <label>Auth mode
          <select name="authMode">
            <option value="local-session" ${settings.server.authMode === 'local-session' ? 'selected' : ''}>local-session</option>
            <option value="password" ${settings.server.authMode === 'password' ? 'selected' : ''}>password</option>
          </select>
        </label>
        <label>Show terminal by default
          <select name="showTerminalMirrorByDefault">
            <option value="true" ${settings.ui.showTerminalMirrorByDefault ? 'selected' : ''}>true</option>
            <option value="false" ${!settings.ui.showTerminalMirrorByDefault ? 'selected' : ''}>false</option>
          </select>
        </label>
        <button class="primary" type="submit">Save settings</button>
      </form>
    </section>
  `;
  views.settings.querySelector('#settings-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const result = await api('/api/settings', {
      method: 'PUT',
      body: JSON.stringify({
        server: {
          host: formData.get('host'),
          port: Number(formData.get('port')),
          authMode: formData.get('authMode'),
        },
        ui: {
          showTerminalMirrorByDefault: formData.get('showTerminalMirrorByDefault') === 'true',
        },
      }),
    });
    state.settings = result.settings;
    alert(result.restartRequired ? 'Settings saved. Restart required for some changes.' : 'Settings saved.');
  });
}

function renderDoctor() {
  show('doctor');
  const doctor = state.doctor;
  views.doctor.innerHTML = `
    <section class="card">
      <h2>Doctor</h2>
      <p>Status: <span class="status-badge">${doctor.status}</span></p>
      <div class="grid-2">
        <div>
          <h3>Checks</h3>
          <div class="list">${doctor.checks.map((check) => `<article class="card"><h4>${check.id}</h4><p>${check.summary}</p><p class="muted">${(check.details || []).join(' • ')}</p></article>`).join('')}</div>
        </div>
        <div>
          <h3>Agents</h3>
          <div class="list">${doctor.agents.map((agent) => `<article class="card"><h4>${agent.agentId}</h4><p>${agent.summary}</p><p class="muted">${(agent.details || []).join(' • ')}</p></article>`).join('')}</div>
        </div>
      </div>
    </section>
  `;
}

async function refreshSessions() {
  state.sessions = (await api('/api/sessions')).items;
  await Promise.all(state.sessions.map(async (session) => {
    const detail = await api(`/api/sessions/${session.id}`);
    state.sessionDetails.set(session.id, detail);
    const history = await api(`/api/sessions/${session.id}/events`);
    state.events.set(session.id, history.items);
  }));
}

async function refreshGlobalData() {
  const [agents, doctor, settings] = await Promise.all([
    api('/api/agents'),
    api('/api/doctor'),
    api('/api/settings'),
  ]);
  state.agents = agents.agents;
  state.doctor = doctor;
  state.settings = settings;
  await refreshSessions();
}

function connectSocket() {
  if (state.socket) state.socket.close();
  const socket = new WebSocket(`${location.origin.replace('http', 'ws')}/api/events`);
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'session.snapshot') {
      state.sessionDetails.set(message.session.id, message.session);
      rerender();
      return;
    }
    if (message.type === 'event') {
      const sessionEvents = state.events.get(message.event.sessionId) || [];
      if (!sessionEvents.some((entry) => entry.id === message.event.id)) sessionEvents.push(message.event);
      state.events.set(message.event.sessionId, sessionEvents);
      const detail = state.sessionDetails.get(message.event.sessionId);
      if (detail) {
        api(`/api/sessions/${message.event.sessionId}`).then((nextDetail) => {
          state.sessionDetails.set(nextDetail.id, nextDetail);
          refreshSessions().then(rerender);
        }).catch(console.error);
      }
      rerender();
    }
  });
  socket.addEventListener('open', () => {
    socket.send(JSON.stringify({ type: 'subscribe' }));
  });
  state.socket = socket;
}

function rerender() {
  if (!state.auth?.authenticated && state.auth?.mode === 'password') {
    renderLogin();
    return;
  }
  const route = currentRoute();
  if (route.route === 'settings') return renderSettings();
  if (route.route === 'doctor') return renderDoctor();
  if (route.route === 'session' && route.id) return renderWorkspace(route.id);
  return renderDashboard();
}

async function bootstrap() {
  state.auth = await api('/api/auth/session').catch(async () => {
    const response = await fetch('/api/auth/session');
    const json = await response.json();
    return json.data;
  });
  state.csrfToken = state.auth?.csrfToken || '';
  if (!state.auth.authenticated && state.auth.mode === 'password') {
    renderLogin();
    return;
  }
  await refreshGlobalData();
  connectSocket();
  rerender();
}

window.addEventListener('hashchange', rerender);
bootstrap().catch((error) => {
  console.error(error);
  views.dashboard.classList.remove('hidden');
  views.dashboard.innerHTML = `<section class="card"><h2>Failed to load application</h2><p>${error.message}</p></section>`;
});
