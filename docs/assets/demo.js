/* Demonstração estática do TCC. Não envia chamados nem autentica usuários reais. */
(() => {
  'use strict';
  const STORE = 'tcc-service-desk-pages-v1';
  const REPO = 'https://github.com/Th3Destroyer/TCC';
  const app = document.getElementById('app');
  const kinds = {incident: 'Incidente', request: 'Requisição de serviço', question: 'Dúvida / orientação'};
  const statuses = {open: 'Aberto', triage: 'Em triagem', in_progress: 'Em atendimento', waiting: 'Aguardando retorno', resolved: 'Resolvido', closed: 'Encerrado'};
  const priorities = {low: 'Baixa', medium: 'Média', high: 'Alta', critical: 'Crítica'};
  const transitions = {open: ['triage', 'in_progress'], triage: ['in_progress', 'waiting'], in_progress: ['waiting', 'resolved'], waiting: ['triage', 'in_progress', 'resolved'], resolved: ['closed', 'triage'], closed: ['triage']};
  let config;
  let state;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const text = value => esc(value).replace(/\n/g, '<br>');
  const icon = name => `<svg class="icon" aria-hidden="true"><use href="assets/icons.svg#icon-${esc(name)}"></use></svg>`;
  const isTech = () => state.role === 'tech';
  const actor = () => isTech() ? 'carlos' : 'ana';
  const person = id => ({ana: 'Ana Silva', carlos: 'Carlos Oliveira', bruno: 'Bruno Santos'}[id] || 'Não atribuído');
  const finished = ticket => ['resolved', 'closed'].includes(ticket.status);
  const date = value => value ? new Intl.DateTimeFormat('pt-BR', {dateStyle: 'short', timeStyle: 'short'}).format(new Date(value)) : '—';
  const reference = ticket => `SD-${new Date(ticket.created).getFullYear()}-${String(ticket.id).padStart(5, '0')}`;
  const badge = ticket => `<span class="badge status-${esc(ticket.status)}">${esc(statuses[ticket.status])}</span>`;
  const priority = ticket => `<span class="priority priority-${esc(ticket.priority)}"><i></i>${esc(priorities[ticket.priority])}</span>`;
  const options = (values, selected) => Object.entries(values).map(([value, label]) => `<option value="${esc(value)}" ${value === selected ? 'selected' : ''}>${esc(label)}</option>`).join('');
  const listOptions = (values, selected) => values.map(value => `<option ${value === selected ? 'selected' : ''}>${esc(value)}</option>`).join('');
  const visibleTickets = () => state.tickets.filter(ticket => isTech() || ticket.requester === actor()).sort((a, b) => new Date(b.created) - new Date(a.created) || b.id - a.id);
  const published = () => state.articles.filter(article => article.published).sort((a, b) => Number(b.featured) - Number(a.featured) || a.title.localeCompare(b.title, 'pt-BR'));
  const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const now = () => new Date().toISOString();
  const field = (label, input, wide = false, help = '') => `<div class="field ${wide ? 'field-wide' : ''}">${label}${input}${help ? `<small class="field-help">${help}</small>` : ''}</div>`;
  const input = (name, label, value = '', extra = '') => field(`<label for="${name}">${label}</label>`, `<input id="${name}" name="${name}" value="${esc(value)}" ${extra}>`);
  const select = (name, label, content) => field(`<label for="${name}">${label}</label>`, `<select id="${name}" name="${name}">${content}</select>`);
  const textarea = (name, label, value = '', rows = 5, extra = '') => field(`<label for="${name}">${label}</label>`, `<textarea id="${name}" name="${name}" rows="${rows}" ${extra}>${esc(value)}</textarea>`, true);
  const pageHeading = (title, subtitle, actions = '', eyebrow = '') => `<div class="page-heading"><div>${eyebrow ? `<div class="eyebrow">${eyebrow}</div>` : ''}<h1>${esc(title)}<span class="title-dot">.</span></h1><p>${esc(subtitle)}</p></div>${actions}</div>`;
  const buttonLink = (href, label, primary = false, symbol = '') => `<a class="btn ${primary ? 'btn-primary' : 'btn-secondary'}" href="#${href}">${symbol ? icon(symbol) : ''}${label}</a>`;
  const empty = (title, body) => `<div class="empty-state"><span class="empty-icon">${icon('ticket')}</span><h3>${esc(title)}</h3><p>${esc(body)}</p>${buttonLink('/novo', 'Abrir um chamado', true)}</div>`;

  function seed() {
    const samples = [
      ['Impressora da recepção não imprime', 'incident', 'Impressoras', 'Saúde', 'high', 'open', null, 'ana'],
      ['Como solicitar acesso ao sistema?', 'question', 'Criação de usuários', 'Finanças', 'low', 'triage', 'carlos', 'ana'],
      ['Computador não liga na secretaria', 'incident', 'Hardware', 'Administração', 'critical', 'in_progress', 'carlos', 'ana'],
      ['Instalação de programa na unidade', 'request', 'Software', 'Educação', 'medium', 'waiting', 'carlos', 'ana'],
      ['Falha na conexão de rede', 'incident', 'Conectividade', 'Obras', 'high', 'resolved', 'carlos', 'ana'],
      ['Ramal da unidade sem sinal', 'incident', 'Telefonia', 'Assistência Social', 'medium', 'closed', 'carlos', 'ana'],
      ['Computador reinicia durante o uso', 'incident', 'Hardware', 'Educação', 'high', 'open', null, 'bruno'],
      ['Dúvida sobre impressão frente e verso', 'question', 'Impressoras', 'Saúde', 'low', 'open', null, 'bruno'],
    ];
    const tickets = samples.map((sample, index) => {
      const [title, kind, category, department, level, status, assigned, requester] = sample;
      const created = new Date(Date.now() - (index % 6) * 86400000 - 3 * 3600000).toISOString();
      const resolved = ['resolved', 'closed'].includes(status);
      return {id: index + 1, title, kind, category, department, priority: level, status, assigned, requester,
        description: 'Registro fictício para conhecer o funcionamento do Service Desk. A unidade precisa de orientação ou suporte para continuar suas atividades.',
        equipment: `PAT-${String(index + 1).padStart(4, '0')}`, created,
        firstResponse: ['in_progress', 'waiting', 'resolved', 'closed'].includes(status) ? new Date(new Date(created).getTime() + 3600000).toISOString() : null,
        resolvedAt: resolved ? new Date(new Date(created).getTime() + 2 * 3600000).toISOString() : null,
        resolution: resolved ? 'Configuração revisada e funcionamento validado com a unidade.' : '',
        version: 1, source: null,
        comments: resolved ? [{author: 'carlos', body: 'Configuração revisada e funcionamento validado com a unidade.', internal: false, created}] : [],
        events: [{author: requester, message: 'Chamado aberto.', created}, ...(assigned ? [{author: 'carlos', message: `Atendimento atualizado: ${statuses[status]}.`, created}] : [])]};
    });
    return {version: 1, role: null, tickets, articles: JSON.parse(JSON.stringify(config.articles)), feedback: {}};
  }

  function save() {
    try { localStorage.setItem(STORE, JSON.stringify(state)); }
    catch { notify('O navegador não permitiu salvar o exemplo. Você pode continuar nesta sessão.', true); }
  }

  function notify(message, error = false) {
    document.querySelector('.demo-toast')?.remove();
    const node = document.createElement('div');
    node.className = `demo-toast${error ? ' error' : ''}`;
    node.setAttribute('role', error ? 'alert' : 'status');
    node.textContent = message;
    document.body.append(node);
    setTimeout(() => node.remove(), 6500);
  }

  function route() {
    const [path, query] = (location.hash.slice(1) || '/').split('?');
    return {path, params: new URLSearchParams(query || '')};
  }

  function go(path) {
    if (location.hash === `#${path}`) render();
    else location.hash = path;
  }

  function updateTicket(ticket, message) {
    ticket.version += 1;
    ticket.events.push({author: actor(), message, created: now()});
    save();
  }

  function lookup(id) { return visibleTickets().find(ticket => ticket.id === Number(id)); }

  function login() {
    return `<div class="demo-login"><div class="login-layout"><section class="login-story"><a class="brand" href="#/entrar"><span class="brand-icon">s<span>${icon('arrow-up-right')}</span></span><span>service desk<small>GESTÃO MUNICIPAL</small></span></a><div><span class="eyebrow">TECNOLOGIA A SERVIÇO DA CIDADE</span><h1>Um só lugar.<br>Todo o suporte<br>que você precisa.</h1><p>Conheça as telas do projeto de Service Desk para a administração pública municipal.</p><div class="login-features"><span>✓ Abertura e acompanhamento de chamados</span><span>✓ Central de ajuda e suporte a dúvidas</span><span>✓ Histórico e indicadores de atendimento</span></div></div><small>Projeto acadêmico · UNIP · Dados fictícios</small></section><section class="login-form-wrap"><div class="login-form"><span class="section-tag">DEMONSTRAÇÃO NAVEGÁVEL</span><h2>Experimente o Service Desk</h2><p class="muted">Escolha um perfil para conhecer as telas.</p><div class="demo-info">Nenhuma senha é necessária. Esta demonstração usa dados fictícios e guarda alterações apenas no seu navegador. Não utilize dados reais.</div><button type="button" class="btn btn-primary full-width" data-action="role" data-role="requester">Entrar como solicitante ${icon('arrow-right')}</button><button type="button" class="btn btn-secondary full-width" data-action="role" data-role="tech">Entrar como técnico de TI ${icon('arrow-right')}</button><p class="login-action-note">Você pode trocar de perfil para acompanhar o mesmo chamado dos dois lados do atendimento.</p><p class="login-help"><a href="${REPO}" target="_blank" rel="noopener noreferrer">Ver o projeto completo em Django no GitHub ↗</a></p></div></section></div></div>`;
  }

  function shell(content, title) {
    const {path} = route();
    const nav = (href, label, symbol, active) => `<a href="#${href}" class="${active ? 'active' : ''}">${icon(symbol)} ${label}</a>`;
    return `<button class="skip-link" type="button" data-action="skip">Pular para o conteúdo</button><aside class="sidebar" aria-label="Menu principal"><a class="brand" href="#/"><span class="brand-icon">s<span>${icon('arrow-up-right')}</span></span><span>service desk<small>GESTÃO MUNICIPAL</small></span></a><div class="workspace-label"><span class="live-dot"></span> Central de suporte de TI</div><div class="nav-label">PRINCIPAL</div><nav>${nav('/', 'Visão geral', 'grid', path === '/')}${nav('/chamados', isTech() ? 'Chamados' : 'Meus chamados', 'ticket', ['/chamados', '/novo', '/chamado'].some(p => path.startsWith(p)))}${nav('/ajuda', 'Central de ajuda', 'help', ['/ajuda', '/artigo', '/duvida'].some(p => path.startsWith(p)))}${isTech() ? nav('/indicadores', 'Indicadores', 'chart', path === '/indicadores') : ''}</nav><div class="sidebar-bottom"><div class="support-card"><span class="support-symbol">✳</span><strong>Suporte que conecta.</strong><p>Conheça o atendimento e a central de ajuda do Service Desk Municipal.</p></div><button type="button" class="demo-reset" data-action="reset">Restaurar dados de exemplo</button><a class="sidebar-caption" href="${REPO}" target="_blank" rel="noopener noreferrer">VER PROJETO NO GITHUB ↗</a></div></aside><div class="app-shell"><header class="topbar"><span class="breadcrumb">Central de suporte <span>/</span> <strong>${esc(title)}</strong></span><div class="demo-role"><span class="avatar">${isTech() ? 'CO' : 'AS'}</span><label class="demo-role-label" for="demo-role">Testar como</label><select id="demo-role" aria-label="Perfil da demonstração"><option value="requester" ${!isTech() ? 'selected' : ''}>Solicitante · Ana</option><option value="tech" ${isTech() ? 'selected' : ''}>Técnico · Carlos</option></select><button class="btn btn-secondary" type="button" data-action="logout">Sair</button></div></header><main id="main-content" class="main-content" tabindex="-1">${content}<footer class="page-footer"><span>Service Desk Municipal · Demonstração</span><span>Projeto acadêmico com dados fictícios.</span></footer></main></div>`;
  }

  function ticketTable(tickets) {
    if (!tickets.length) return empty('Nenhum chamado encontrado', 'Ajuste os filtros ou registre uma nova solicitação de exemplo.');
    return `<div class="table-scroll"><table><thead><tr><th>Chamado</th><th>Unidade</th><th>Prioridade</th><th>Situação</th><th>Responsável</th><th>Abertura</th></tr></thead><tbody>${tickets.map(ticket => `<tr><td><a class="ticket-title" href="#/chamado/${ticket.id}">${esc(ticket.title)}</a><span class="ticket-meta">${reference(ticket)} · ${esc(ticket.category)} · ${esc(kinds[ticket.kind])}</span></td><td>${esc(ticket.department)}</td><td>${priority(ticket)}</td><td>${badge(ticket)}</td><td>${person(ticket.assigned)}</td><td class="date-cell">${date(ticket.created)}</td></tr>`).join('')}</tbody></table></div>`;
  }

  function metrics(tickets) {
    const active = tickets.filter(ticket => !finished(ticket));
    const grouped = key => [...new Set(tickets.map(t => t[key]))].map(name => ({name, count: tickets.filter(t => t[key] === name).length})).sort((a, b) => b.count - a.count);
    const average = key => {
      const samples = tickets.filter(t => t[key]);
      return samples.length ? (samples.reduce((total, ticket) => total + (new Date(ticket[key]) - new Date(ticket.created)) / 3600000, 0) / samples.length).toFixed(1).replace('.', ',') : '—';
    };
    return {active: active.length, progress: tickets.filter(t => t.status === 'in_progress').length, resolved: tickets.filter(finished).length, critical: active.filter(t => t.priority === 'critical').length, categories: grouped('category'), departments: grouped('department'), response: average('firstResponse'), resolution: average('resolvedAt')};
  }

  function bars(groups, total) {
    return groups.map(group => `<div class="category-item"><div><span>${esc(group.name)}</span><strong>${group.count}</strong></div><div class="progress-track"><span style="width:${total ? group.count / total * 100 : 0}%"></span></div></div>`).join('') || '<p class="muted">Sem registros.</p>';
  }

  function dashboard() {
    const tickets = visibleTickets();
    const m = metrics(tickets);
    const cards = [['Em aberto', m.active, 'ticket', 'mint', 'active'], ['Em atendimento', m.progress, 'clock', 'blue', 'in_progress'], ['Resolvidos ou encerrados', m.resolved, 'check', 'green', 'finished'], ['Prioridade crítica', m.critical, 'help', 'peach', 'active&priority=critical']];
    const days = Array.from({length: 7}, (_, index) => { const day = new Date(Date.now() - (6 - index) * 86400000); return {label: day.toLocaleDateString('pt-BR', {day: '2-digit', month: '2-digit'}), count: tickets.filter(t => new Date(t.created).toDateString() === day.toDateString()).length}; });
    const max = Math.max(1, ...days.map(day => day.count));
    return pageHeading('Visão geral', `Olá, ${isTech() ? 'Carlos' : 'Ana'}. Acompanhe o que acontece no suporte.`, buttonLink('/novo', 'Novo chamado', true, 'plus'), 'SEU PONTO DE CONEXÃO COM A TI') + `<div class="overview-banner"><div class="banner-icon">${icon('arrow-up-right')}</div><div><strong>Um atendimento melhor começa com um bom registro.</strong><p>Centralize as solicitações e acompanhe cada etapa, da abertura à solução.</p></div><span class="banner-label">${isTech() ? 'Visão da equipe de TI' : 'Seus atendimentos'}</span></div><div class="stat-grid">${cards.map(([label, count, symbol, color, status]) => `<a class="stat-card" href="#/chamados?status=${status}"><div class="stat-top"><span>${label}</span><span class="stat-icon ${color}">${icon(symbol)}</span></div><strong>${String(count).padStart(2, '0')}</strong><small>Dados de exemplo do atendimento</small></a>`).join('')}</div><div class="dashboard-grid"><section class="panel"><div class="panel-heading"><div><h2>Movimentação de chamados</h2><p>Solicitações nos últimos sete dias</p></div></div><div class="chart-legend"><span></span> Chamados abertos</div><div class="bar-chart" role="img" aria-label="Quantidade diária de chamados">${days.map(day => `<div class="chart-column"><span class="bar-number">${day.count}</span><div class="chart-track"><div class="chart-bar" style="height:${Math.max(3, day.count / max * 100)}%"></div></div><span class="bar-label">${day.label}</span></div>`).join('')}</div></section><section class="panel"><div class="panel-heading"><div><h2>Por categoria</h2><p>Distribuição dos chamados</p></div></div><div class="category-list">${bars(m.categories, tickets.length)}</div></section></div><section class="panel"><div class="panel-heading"><div><h2>Chamados recentes</h2><p>Últimas solicitações registradas</p></div><a class="text-link" href="#/chamados">Ver todos →</a></div>${ticketTable(tickets.slice(0, 6))}</section>`;
  }

  function filteredTickets(params) {
    return visibleTickets().filter(ticket => {
      const query = normalize(params.get('q') || '');
      if (query && !normalize(`${ticket.title} ${ticket.description} ${ticket.equipment} ${reference(ticket)}`).includes(query)) return false;
      for (const key of ['kind', 'priority', 'category', 'department']) if (params.get(key) && ticket[key] !== params.get(key)) return false;
      const status = params.get('status');
      if (status === 'active' && finished(ticket)) return false;
      if (status === 'finished' && !finished(ticket)) return false;
      if (status && !['active', 'finished'].includes(status) && ticket.status !== status) return false;
      if (isTech() && params.get('mine') && ticket.assigned !== actor()) return false;
      if (isTech() && params.get('unassigned') && (ticket.assigned || finished(ticket))) return false;
      return true;
    });
  }

  function ticketList(params) {
    const tickets = visibleTickets();
    const result = filteredTickets(params);
    const actions = `<div class="heading-actions">${buttonLink('/duvida', 'Enviar dúvida', false, 'message')}${buttonLink('/novo', 'Novo chamado', true, 'plus')}</div>`;
    const filter = (name, label, values) => `<label class="sr-only" for="f-${name}">${label}</label><select name="${name}" id="f-${name}"><option value="">${label}</option>${options(values, params.get(name))}</select>`;
    return pageHeading(isTech() ? 'Chamados' : 'Meus chamados', 'Acompanhe incidentes, solicitações de serviço e dúvidas em um só lugar.', actions) + `<div class="queue-summary"><a href="#/chamados"><strong>${tickets.length}</strong><span>Total de chamados</span></a><a href="#/chamados?status=active"><strong>${tickets.filter(t => !finished(t)).length}</strong><span>Em aberto</span></a><a href="#/chamados?kind=question"><strong>${tickets.filter(t => t.kind === 'question').length}</strong><span>Dúvidas e orientações</span></a>${isTech() ? `<a href="#/chamados?unassigned=1"><strong>${tickets.filter(t => !t.assigned && !finished(t)).length}</strong><span>Aguardando responsável</span></a>` : `<a href="#/ajuda">${icon('book')}<span>Central de ajuda</span></a>`}</div><section class="panel"><form class="filters" data-action="filter-tickets"><div class="search-field"><label class="sr-only" for="ticket-search">Buscar chamados</label><span>${icon('search')}</span><input id="ticket-search" name="q" value="${esc(params.get('q') || '')}" type="search" placeholder="Assunto, protocolo ou patrimônio"></div>${filter('kind', 'Todos os tipos', kinds)}${filter('status', 'Todas as situações', {active: 'Em aberto (ativos)', finished: 'Resolvidos ou encerrados', ...statuses})}${filter('priority', 'Todas as prioridades', priorities)}${filter('category', 'Todas as categorias', Object.fromEntries(config.categories.map(c => [c, c])))}${isTech() ? `<label class="checkbox-label"><input type="checkbox" name="mine" value="1" ${params.get('mine') ? 'checked' : ''}> Atribuídos a mim</label><label class="checkbox-label"><input type="checkbox" name="unassigned" value="1" ${params.get('unassigned') ? 'checked' : ''}> Sem responsável</label>` : ''}<button class="btn btn-secondary" type="submit">Filtrar</button><a class="clear-link" href="#/chamados">Limpar</a></form><div class="list-summary"><span><strong>${result.length}</strong> chamado(s) encontrado(s)</span>${isTech() ? '<button class="btn btn-secondary" data-action="csv" type="button">Exportar CSV</button>' : ''}</div>${ticketTable(result)}</section>`;
  }

  function newTicket(question, params) {
    const source = published().find(article => article.id === Number(params.get('article')));
    return `<a class="back-link" href="#/${question ? 'ajuda' : 'chamados'}">← Voltar</a>` + pageHeading(question ? 'Envie sua dúvida' : 'Novo chamado', question ? 'Conte o que precisa saber. Experimente o acompanhamento pelo chamado.' : 'Conte o que aconteceu. Quanto mais detalhes, melhor poderemos atender.', '', 'ESTAMOS AQUI PARA AJUDAR') + `${source ? `<div class="alert info">Orientação consultada: ${esc(source.title)}</div>` : ''}<div class="form-layout"><section class="panel form-panel"><div class="panel-heading"><div><h2>${question ? 'O que você precisa saber?' : 'Informações da solicitação'}</h2><p>Use apenas dados fictícios neste exemplo.</p></div></div><form data-action="new-ticket" class="demo-form"><input type="hidden" name="source" value="${source?.id || ''}"><div class="form-grid">${input('title', question ? 'Assunto da dúvida *' : 'Assunto *', source ? `Dúvida sobre: ${source.title}`.slice(0, 160) : '', 'required maxlength="160"')}${question ? '<input type="hidden" name="kind" value="question">' : select('kind', 'Tipo *', options(kinds, 'incident'))}${select('category', 'Categoria *', '<option value="">Selecione uma categoria</option>' + listOptions(config.categories, source?.category || ''))}${select('department', 'Unidade / secretaria *', listOptions(config.departments, 'Saúde'))}${select('priority', 'Prioridade *', options(priorities, question ? 'low' : 'medium'))}${question ? '' : input('equipment', 'Equipamento / patrimônio', '', 'maxlength="100"')}${textarea('description', question ? 'Sua dúvida *' : 'Descrição *', '', 6, 'required maxlength="10000"')}</div><div class="form-actions">${buttonLink('/chamados', 'Cancelar')}<button class="btn btn-primary" type="submit">${question ? 'Enviar dúvida' : 'Registrar chamado'} ${icon('arrow-right')}</button></div></form></section><aside class="help-panel"><span class="help-icon">${icon('message')}</span><h3>Uma conversa que fica registrada.</h3><p>Você poderá trocar de perfil para acompanhar a mesma solicitação como usuário e como técnico.</p><hr><h4>Como funciona?</h4><ol><li>Registre a solicitação.</li><li>Troque para o perfil Técnico.</li><li>Assuma e responda ao chamado.</li><li>Volte ao Solicitante para confirmar.</li></ol><p class="privacy-note">Demonstração local: nada será enviado à equipe de uma prefeitura. Não use dados reais.</p>${buttonLink('/ajuda', 'Consultar central de ajuda')}</aside></div>`;
  }

  function ticketDetail(id) {
    const ticket = lookup(id);
    if (!ticket) return empty('Chamado não encontrado', 'O chamado não existe neste exemplo ou pertence a outro solicitante.');
    const source = published().find(a => a.id === ticket.source);
    const comments = ticket.comments.filter(c => isTech() || !c.internal);
    let techForm = '';
    if (isTech()) {
      const allowed = Object.fromEntries([ticket.status, ...transitions[ticket.status]].map(key => [key, statuses[key]]));
      techForm = `<section class="panel"><div class="panel-heading"><div><h2>Área de atendimento</h2><p>Classifique, encaminhe e atualize.</p></div></div><div class="panel-body"><form data-action="update-ticket" data-id="${ticket.id}"><input type="hidden" name="version" value="${ticket.version}">${select('kind', 'Tipo', options(kinds, ticket.kind))}${select('category', 'Categoria', listOptions(config.categories, ticket.category))}${select('priority', 'Prioridade', options(priorities, ticket.priority))}${select('assigned', 'Técnico responsável', options({'': 'Não atribuído', carlos: 'Carlos Oliveira'}, ticket.assigned || ''))}${select('status', 'Situação', options(allowed, ticket.status))}${textarea('resolution', ticket.kind === 'question' ? 'Resposta / orientação' : 'Solução aplicada', ticket.resolution, 4, 'maxlength="10000"')}<button class="btn btn-primary full-width" type="submit">Salvar atendimento</button></form></div></section>`;
    }
    const requesterActions = ticket.requester === actor() && finished(ticket) ? `<div class="solution-actions">${ticket.status === 'resolved' ? `<button class="btn btn-primary" type="button" data-action="close" data-id="${ticket.id}">Confirmar solução e encerrar</button>` : ''}<button class="btn btn-secondary" type="button" data-action="reopen" data-id="${ticket.id}">Reabrir chamado</button></div>` : '';
    return `<a class="back-link" href="#/chamados">← Voltar para chamados</a><div class="page-heading detail-heading"><div><div class="eyebrow">${reference(ticket)} · ${esc(kinds[ticket.kind])}</div><h1>${esc(ticket.title)}</h1><p>Aberto por ${person(ticket.requester)} em ${date(ticket.created)}</p></div>${badge(ticket)}</div>${isTech() && !ticket.assigned && !finished(ticket) ? `<div class="claim-banner"><div><strong>Este chamado ainda não tem responsável.</strong><p>Assuma o atendimento para organizar a fila.</p></div><button class="btn btn-primary" type="button" data-action="claim" data-id="${ticket.id}">Assumir chamado</button></div>` : ''}${source ? `<div class="alert info">Orientação consultada: <a class="text-link" href="#/artigo/${source.id}">${esc(source.title)}</a></div>` : ''}<div class="detail-grid"><div><section class="panel"><div class="panel-heading"><h2>Sobre a solicitação</h2>${priority(ticket)}</div><div class="panel-body"><div class="description-text">${text(ticket.description)}</div><dl class="info-grid"><div><dt>Unidade / secretaria</dt><dd>${esc(ticket.department)}</dd></div><div><dt>Categoria</dt><dd>${esc(ticket.category)}</dd></div><div><dt>Equipamento / patrimônio</dt><dd>${esc(ticket.equipment || 'Não informado')}</dd></div><div><dt>Responsável</dt><dd>${person(ticket.assigned)}</dd></div></dl></div></section>${ticket.resolution ? `<section class="panel solution-panel"><div class="panel-heading"><h2>✓ ${ticket.kind === 'question' ? 'Resposta da equipe de TI' : 'Solução aplicada'}</h2></div><div class="panel-body"><div class="description-text">${text(ticket.resolution)}</div>${requesterActions}</div></section>` : requesterActions}<section class="panel"><div class="panel-heading"><div><h2>Conversa e atualizações</h2><p>Mensagens sobre este atendimento</p></div></div><div class="panel-body demo-messages">${comments.map(comment => `<article class="comment ${comment.internal ? 'internal-comment' : ''}"><div class="comment-header"><strong>${person(comment.author)}</strong>${comment.internal ? '<span class="subtle-pill">Nota interna</span>' : ''}<time>${date(comment.created)}</time></div><div class="comment-body">${text(comment.body)}</div></article>`).join('') || '<p class="muted">Ainda não há mensagens neste chamado.</p>'}${ticket.status !== 'closed' ? `<form data-action="comment" data-id="${ticket.id}">${textarea('body', 'Mensagem', '', 4, 'required maxlength="10000"')}${isTech() ? '<div class="field"><label class="checkbox-label"><input type="checkbox" name="internal"> Nota interna (apenas TI)</label></div>' : ''}<button class="btn btn-primary" type="submit">Enviar mensagem</button></form>` : '<p class="demo-system-note">Reabra o chamado para enviar novas mensagens.</p>'}</div></section></div><aside>${techForm}<section class="panel"><div class="panel-heading"><h2>Histórico do chamado</h2></div><div class="panel-body"><ol class="timeline">${[...ticket.events].reverse().map(event => `<li><strong>${text(event.message)}</strong><span>${person(event.author)} · ${date(event.created)}</span></li>`).join('')}</ol></div></section></aside></div>`;
  }

  function helpCenter(params) {
    const all = published();
    const query = normalize(params.get('q') || '');
    const category = params.get('category');
    const articles = all.filter(a => (!query || normalize(`${a.title} ${a.summary} ${a.body}`).includes(query)) && (!category || (category === 'general' ? !a.category : a.category === category)));
    const card = article => `<a class="article-card" href="#/artigo/${article.id}"><div class="article-card-top"><span class="subtle-pill">${esc(article.category || 'Orientações gerais')}</span>${icon('book')}</div><h3>${esc(article.title)}</h3><p>${esc(article.summary)}</p><span class="text-link">Ler orientação ${icon('arrow-right')}</span></a>`;
    return pageHeading('Como podemos ajudar?', 'Encontre uma orientação ou converse com a equipe de TI.', isTech() ? buttonLink('/artigos', 'Gerenciar artigos', false, 'book') : '', 'ORIENTAÇÃO PARA O DIA A DIA') + `<section class="help-hero"><span class="hero-symbol">${icon('help')}</span><div><h2>Uma resposta pode estar mais perto do que você imagina.</h2><p>Pesquise por senha, impressora, rede ou outro assunto.</p></div><form class="help-search" data-action="search-help"><label class="sr-only" for="help-search">Pesquisar na central de ajuda</label><span>${icon('search')}</span><input id="help-search" name="q" type="search" maxlength="200" value="${esc(params.get('q') || '')}" placeholder="Qual é a sua dúvida?"><input type="hidden" name="category" value="${esc(category || '')}"><button class="btn btn-primary" type="submit">Buscar orientação</button></form></section><div class="help-shortcuts"><a class="help-shortcut" href="#/novo"><span class="shortcut-icon">${icon('ticket')}</span><div><strong>Preciso de suporte técnico</strong><p>Registre uma falha ou solicite um serviço.</p></div>${icon('arrow-up-right')}</a><a class="help-shortcut" href="#/duvida"><span class="shortcut-icon">${icon('message')}</span><div><strong>Quero tirar uma dúvida</strong><p>Experimente enviar uma pergunta.</p></div>${icon('arrow-up-right')}</a><a class="help-shortcut" href="#/chamados?kind=question"><span class="shortcut-icon">${icon('clock')}</span><div><strong>Acompanhar dúvidas</strong><p>Veja as perguntas registradas.</p></div>${icon('arrow-up-right')}</a></div><div class="help-layout"><div><div class="section-heading"><div><h2>Orientações e tutoriais</h2><p class="muted">${articles.length} resultado(s)</p></div><a class="text-link" href="#/ajuda">Limpar filtros</a></div><div class="article-grid">${articles.map(card).join('') || empty('Nenhuma orientação encontrada', 'Tente outra palavra ou envie uma dúvida.')}</div><section class="panel"><div class="panel-heading"><h2>Perguntas frequentes</h2></div><div class="faq-list">${all.filter(a => a.featured).slice(0, 5).map(article => `<details><summary>${esc(article.title)}${icon('chevron')}</summary><div><p>${text(article.body.slice(0, 320))}…</p><a class="text-link" href="#/artigo/${article.id}">Ver orientação completa →</a></div></details>`).join('')}</div></section></div><aside><section class="panel"><div class="panel-heading"><h2>Explorar por assunto</h2></div><nav class="help-categories" aria-label="Assuntos"><a href="#/ajuda" class="${!category ? 'selected' : ''}">Todos os assuntos <span>${all.length}</span></a>${[['general', 'Orientações gerais'], ...config.categories.map(c => [c, c])].map(([value, label]) => `<a href="#/ajuda?category=${encodeURIComponent(value)}" class="${category === value ? 'selected' : ''}">${esc(label)}<span>${all.filter(a => value === 'general' ? !a.category : a.category === value).length}</span></a>`).join('')}</nav></section><section class="help-panel"><span class="help-icon">${icon('message')}</span><h3>Não encontrou sua resposta?</h3><p>Envie uma dúvida de exemplo e acompanhe a resposta como solicitante e como técnico.</p>${buttonLink('/duvida', 'Falar com o suporte', true)}<p class="privacy-note">Esta demonstração não envia mensagens a uma equipe real.</p></section></aside></div>`;
  }

  function articleDetail(id) {
    const article = state.articles.find(a => a.id === Number(id) && (a.published || isTech()));
    if (!article) return empty('Artigo não encontrado', 'A orientação não está publicada ou não existe neste exemplo.');
    const vote = state.feedback[`${actor()}:${article.id}`];
    return `<a class="back-link" href="#/ajuda">← Voltar para a central de ajuda</a>${!article.published ? '<div class="alert info">Rascunho: visível apenas no perfil de técnico.</div>' : ''}<div class="help-layout article-layout"><article class="panel article-reading"><header><span class="subtle-pill">${esc(article.category || 'Orientações gerais')}</span><h1>${esc(article.title)}</h1><p class="article-intro">${esc(article.summary)}</p><p class="article-byline">Equipe de TI · Orientação de exemplo</p></header><div class="article-body">${text(article.body)}</div>${article.published ? `<footer class="article-feedback"><h2>Esta orientação ajudou você?</h2><p>${vote !== undefined ? 'Avaliação registrada. Você pode alterá-la abaixo.' : 'Sua resposta ajuda a melhorar as orientações.'}</p><div class="feedback-buttons"><button class="btn ${vote === true ? 'btn-primary' : 'btn-secondary'}" data-action="feedback" data-id="${article.id}" data-value="yes" aria-pressed="${vote === true}" type="button">Sim, ajudou</button><button class="btn ${vote === false ? 'btn-primary' : 'btn-secondary'}" data-action="feedback" data-id="${article.id}" data-value="no" aria-pressed="${vote === false}" type="button">Ainda preciso de ajuda</button></div></footer>` : ''}</article><aside><section class="help-panel"><span class="help-icon">${icon('message')}</span><h3>Vamos conversar?</h3><p>Se a orientação não resolveu, envie uma pergunta e acompanhe pelo chamado.</p>${buttonLink(`/duvida${article.published ? `?article=${article.id}` : ''}`, 'Enviar dúvida sobre este artigo', true)}</section>${isTech() ? `<section class="panel"><div class="panel-body article-tools"><h2>Área da equipe de TI</h2><p class="muted">${article.published ? 'Publicado' : 'Rascunho'}</p>${buttonLink(`/editar-artigo/${article.id}`, 'Editar orientação')}<a class="text-link" href="#/artigos">Gerenciar todos os artigos →</a></div></section>` : ''}</aside></div>`;
  }

  function articleManage(params) {
    if (!isTech()) return empty('Área da equipe de TI', 'Troque para o perfil Técnico para gerenciar as orientações.');
    const query = normalize(params.get('q') || '');
    const articles = state.articles.filter(a => normalize(`${a.title} ${a.summary}`).includes(query));
    return pageHeading('Artigos de ajuda', 'Crie, revise e publique orientações neste exemplo.', buttonLink('/novo-artigo', 'Novo artigo', true, 'plus')) + `<section class="panel"><form class="filters" data-action="search-articles"><label class="sr-only" for="article-search">Buscar artigos</label><input id="article-search" name="q" type="search" value="${esc(params.get('q') || '')}" placeholder="Buscar artigo"><button class="btn btn-secondary" type="submit">Buscar</button></form><div class="table-scroll"><table><thead><tr><th>Artigo</th><th>Categoria</th><th>Publicação</th><th>Ações</th></tr></thead><tbody>${articles.map(a => `<tr><td><a class="ticket-title" href="#/artigo/${a.id}">${esc(a.title)}</a></td><td>${esc(a.category || 'Geral')}</td><td><span class="badge status-${a.published ? 'resolved' : 'triage'}">${a.published ? 'Publicado' : 'Rascunho'}</span></td><td><a class="text-link" href="#/editar-artigo/${a.id}">Editar →</a></td></tr>`).join('')}</tbody></table></div></section>`;
  }

  function articleEdit(id) {
    if (!isTech()) return empty('Área da equipe de TI', 'Troque para o perfil Técnico para editar orientações.');
    const article = id ? state.articles.find(a => a.id === Number(id)) : null;
    if (id && !article) return empty('Artigo não encontrado', 'Confira o endereço da orientação.');
    return `<a class="back-link" href="#/artigos">← Voltar para os artigos</a>` + pageHeading(article ? 'Editar artigo' : 'Novo artigo', 'Escreva uma orientação de exemplo em texto simples.') + `<div class="form-layout"><section class="panel form-panel"><div class="panel-heading"><h2>Conteúdo da orientação</h2></div><form data-action="save-article" data-id="${article?.id || ''}"><div class="form-grid article-form-grid">${input('title', 'Título *', article?.title || '', 'required maxlength="160"')}${textarea('summary', 'Resumo *', article?.summary || '', 2, 'required maxlength="260"')}${select('category', 'Categoria', '<option value="">Orientações gerais</option>' + listOptions(config.categories, article?.category))}${textarea('body', 'Orientações *', article?.body || '', 12, 'required maxlength="20000"')}<div class="field"><label class="checkbox-label"><input type="checkbox" name="featured" ${article?.featured ? 'checked' : ''}> Destacar como pergunta frequente</label></div><div class="field"><label class="checkbox-label"><input type="checkbox" name="published" ${article?.published ? 'checked' : ''}> Publicar na central de ajuda</label></div></div><div class="form-actions">${buttonLink('/artigos', 'Cancelar')}<button class="btn btn-primary" type="submit">Salvar orientação</button></div></form></section><aside class="help-panel"><h3>Compartilhe uma boa orientação.</h3><p>Artigos não publicados ficam como rascunho, visíveis apenas no perfil Técnico.</p><p class="privacy-note">Nesta demonstração, o conteúdo fica apenas neste navegador.</p></aside></div>`;
  }

  function reports() {
    if (!isTech()) return empty('Área da equipe de TI', 'Troque para o perfil Técnico para consultar indicadores globais.');
    const tickets = visibleTickets();
    const m = metrics(tickets);
    return pageHeading('Indicadores', 'Um retrato dos chamados e dos tempos de atendimento de exemplo.') + `<div class="stat-grid reports-stats">${[['Total de chamados', tickets.length], ['Primeira resposta média', `${m.response} h`], ['Tempo médio até a solução', `${m.resolution} h`]].map(([label, value]) => `<div class="stat-card"><div class="stat-top"><span>${label}</span></div><strong>${value}</strong><small>Dados fictícios da demonstração</small></div>`).join('')}</div><div class="alert info">Tempos em horas corridas desde a abertura. Chamados sem o respectivo marco não entram na média. A demonstração não estabelece prazos de atendimento.</div><div class="dashboard-grid"><section class="panel"><div class="panel-heading"><h2>Demandas por unidade</h2></div><div class="category-list">${bars(m.departments, tickets.length)}</div></section><section class="panel"><div class="panel-heading"><h2>Distribuição por categoria</h2></div><div class="category-list">${bars(m.categories, tickets.length)}</div></section></div>`;
  }

  function render() {
    const {path, params} = route();
    let content;
    let title = 'Visão geral';
    if (!state.role || path === '/entrar') content = login();
    else {
      if (path === '/') content = dashboard();
      else if (path === '/chamados') { content = ticketList(params); title = 'Chamados'; }
      else if (path === '/novo' || path === '/duvida') { content = newTicket(path === '/duvida', params); title = path === '/duvida' ? 'Enviar dúvida' : 'Novo chamado'; }
      else if (/^\/chamado\/\d+$/.test(path)) { content = ticketDetail(path.split('/')[2]); title = 'Detalhes do chamado'; }
      else if (path === '/ajuda') { content = helpCenter(params); title = 'Central de ajuda'; }
      else if (/^\/artigo\/\d+$/.test(path)) { content = articleDetail(path.split('/')[2]); title = 'Central de ajuda'; }
      else if (path === '/artigos') { content = articleManage(params); title = 'Artigos de ajuda'; }
      else if (path === '/novo-artigo' || /^\/editar-artigo\/\d+$/.test(path)) { content = articleEdit(path.split('/')[2]); title = 'Artigos de ajuda'; }
      else if (path === '/indicadores') { content = reports(); title = 'Indicadores'; }
      else content = empty('Página não encontrada', 'Use o menu para navegar pelas telas.');
      content = shell(content, title);
    }
    app.innerHTML = `<div class="demo-notice" role="note">${icon('help')} Demonstração do TCC · Dados fictícios · Alterações apenas neste navegador</div>${content}`;
    document.title = `${title} · Service Desk Municipal · Demonstração`;
    window.scrollTo(0, 0);
  }

  document.addEventListener('click', event => {
    const target = event.target.closest('[data-action]');
    if (!target || target.tagName === 'FORM') return;
    const action = target.dataset.action;
    if (action === 'skip') { document.getElementById('main-content')?.focus(); return; }
    if (action === 'role') { state.role = target.dataset.role === 'tech' ? 'tech' : 'requester'; save(); go('/'); }
    if (action === 'logout') { state.role = null; save(); go('/entrar'); }
    if (action === 'reset' && confirm('Restaurar os dados fictícios? Os exemplos criados neste navegador serão apagados.')) { const role = state.role; state = seed(); state.role = role; save(); go('/'); notify('Dados de exemplo restaurados.'); }
    if (action === 'feedback') { const a = published().find(article => article.id === Number(target.dataset.id)); if (!a) return; state.feedback[`${actor()}:${a.id}`] = target.dataset.value === 'yes'; save(); render(); notify('Avaliação de exemplo registrada.'); }
    if (['claim', 'close', 'reopen'].includes(action)) {
      const ticket = lookup(target.dataset.id);
      if (!ticket) return;
      if (action === 'claim') {
        if (!isTech() || ticket.assigned || finished(ticket)) return notify('Esse chamado não está disponível para assumir.', true);
        ticket.assigned = actor();
        if (ticket.status === 'open') ticket.status = 'triage';
        updateTicket(ticket, 'Carlos Oliveira assumiu o chamado.');
      }
      if (action === 'close') {
        if (ticket.requester !== actor() || ticket.status !== 'resolved') return;
        ticket.status = 'closed'; updateTicket(ticket, 'Solução confirmada pelo solicitante. Chamado encerrado.');
      }
      if (action === 'reopen') {
        if (ticket.requester !== actor() || !finished(ticket)) return;
        ticket.status = 'triage'; ticket.resolution = ''; ticket.resolvedAt = null;
        updateTicket(ticket, 'Chamado reaberto pelo solicitante e devolvido à triagem.');
      }
      render(); notify('Chamado de exemplo atualizado.');
    }
    if (action === 'csv' && isTech()) {
      const rows = [['Protocolo', 'Assunto', 'Tipo', 'Unidade', 'Categoria', 'Prioridade', 'Situação'], ...filteredTickets(route().params).map(t => [reference(t), t.title, kinds[t.kind], t.department, t.category, priorities[t.priority], statuses[t.status]])];
      const csv = '\uFEFF' + rows.map(row => row.map(v => { let value = String(v); if (/^[\s]*[=+\-@]/.test(value)) value = "'" + value; return `"${value.replace(/"/g, '""')}"`; }).join(';')).join('\r\n');
      const url = URL.createObjectURL(new Blob([csv], {type: 'text/csv;charset=utf-8'}));
      const link = document.createElement('a'); link.href = url; link.download = 'chamados-demonstracao.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  });

  document.addEventListener('change', event => {
    if (event.target.id === 'demo-role') { state.role = event.target.value === 'tech' ? 'tech' : 'requester'; save(); render(); }
  });

  document.addEventListener('submit', event => {
    const form = event.target;
    if (!form.dataset.action) return;
    event.preventDefault();
    if (!form.reportValidity()) return;
    const values = Object.fromEntries(new FormData(form));
    const action = form.dataset.action;
    if (['filter-tickets', 'search-help', 'search-articles'].includes(action)) {
      const base = {'filter-tickets': '/chamados', 'search-help': '/ajuda', 'search-articles': '/artigos'}[action];
      const params = new URLSearchParams(Object.entries(values).filter(([, value]) => value));
      go(`${base}${params.size ? '?' + params : ''}`); return;
    }
    if (action === 'new-ticket') {
      if (!values.title.trim() || !values.description.trim() || !config.categories.includes(values.category)) return notify('Preencha assunto, categoria e descrição.', true);
      const id = Math.max(0, ...state.tickets.map(t => t.id)) + 1;
      const ticket = {id, title: values.title.trim(), description: values.description.trim(), kind: Object.hasOwn(kinds, values.kind) ? values.kind : 'incident', category: values.category, department: values.department, priority: Object.hasOwn(priorities, values.priority) ? values.priority : 'medium', equipment: values.equipment || '', requester: actor(), assigned: null, status: 'open', created: now(), firstResponse: null, resolvedAt: null, resolution: '', version: 1, source: published().find(a => a.id === Number(values.source))?.id || null, comments: [], events: [{author: actor(), message: 'Chamado aberto.', created: now()}]};
      state.tickets.push(ticket); save(); go(`/chamado/${id}`); notify(`${reference(ticket)} criado somente nesta demonstração.`); return;
    }
    if (action === 'save-article') {
      if (!isTech()) return;
      if (!values.title.trim() || !values.summary.trim() || !values.body.trim()) return notify('Preencha título, resumo e orientações.', true);
      let article = state.articles.find(a => a.id === Number(form.dataset.id));
      if (!article) { article = {id: Math.max(0, ...state.articles.map(a => a.id)) + 1}; state.articles.push(article); }
      Object.assign(article, {title: values.title.trim(), summary: values.summary.trim(), body: values.body.trim(), category: values.category || null, featured: Boolean(values.featured), published: Boolean(values.published)});
      save(); go(`/artigo/${article.id}`); notify(article.published ? 'Orientação publicada neste exemplo.' : 'Rascunho de exemplo salvo.'); return;
    }
    const ticket = lookup(form.dataset.id);
    if (!ticket) return;
    if (action === 'comment') {
      if (ticket.status === 'closed' || !values.body.trim()) return notify('Escreva a mensagem em um chamado que não esteja encerrado.', true);
      const internal = isTech() && Boolean(values.internal);
      ticket.comments.push({author: actor(), body: values.body.trim(), internal, created: now()});
      if (isTech() && !internal && ticket.requester !== actor() && !ticket.firstResponse) ticket.firstResponse = now();
      ticket.version += 1; save(); render(); notify('Mensagem registrada somente no exemplo.'); return;
    }
    if (action === 'update-ticket') {
      if (!isTech()) return;
      if (ticket.version !== Number(values.version)) return notify('O chamado mudou. Recarregue a tela.', true);
      if (values.status !== ticket.status && !transitions[ticket.status].includes(values.status)) return notify('Essa mudança de situação não está disponível.', true);
      if (['in_progress', 'waiting', 'resolved', 'closed'].includes(values.status) && !values.assigned) return notify('Defina um responsável para o atendimento.', true);
      if (['resolved', 'closed'].includes(values.status) && !values.resolution.trim()) return notify('Descreva a resposta ou solução aplicada.', true);
      const old = ticket.status;
      const oldResolution = ticket.resolution;
      Object.assign(ticket, {kind: values.kind, category: values.category, priority: values.priority, assigned: values.assigned || null, status: values.status, resolution: values.resolution.trim()});
      if (['resolved', 'closed'].includes(old) && ticket.status === 'triage') { ticket.resolution = ''; ticket.resolvedAt = null; }
      if (ticket.status === 'in_progress' && !ticket.firstResponse) ticket.firstResponse = now();
      if (ticket.status === 'resolved') { if (!ticket.resolvedAt) ticket.resolvedAt = now(); if (oldResolution !== ticket.resolution || old !== 'resolved') ticket.comments.push({author: actor(), body: `Solução / orientação:\n${ticket.resolution}`, internal: false, created: now()}); }
      updateTicket(ticket, `Atendimento atualizado: ${statuses[old]} → ${statuses[ticket.status]}. Responsável: ${person(ticket.assigned)}.`);
      render(); notify('Atendimento de exemplo atualizado.');
    }
  });

  window.addEventListener('hashchange', () => state && render());
  fetch('assets/data.json', {cache: 'no-cache'}).then(response => {
    if (!response.ok) throw new Error('Não foi possível carregar as orientações.');
    return response.json();
  }).then(data => {
    config = data;
    try { const stored = JSON.parse(localStorage.getItem(STORE)); if (stored?.version === 1 && Array.isArray(stored.tickets) && Array.isArray(stored.articles) && stored.feedback && [null, 'requester', 'tech'].includes(stored.role)) state = stored; }
    catch { /* Um armazenamento vazio ou indisponível não bloqueia a demonstração. */ }
    if (!state) state = seed();
    render();
  }).catch(error => { app.innerHTML = `<div class="empty-state"><h1>Não foi possível carregar a demonstração</h1><p>${esc(error.message)}</p><p>Recarregue a página ou acesse o <a href="${REPO}">repositório do projeto</a>.</p></div>`; });
})();
