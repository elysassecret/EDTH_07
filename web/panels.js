/* panels.js — WebSocket, state, DOM panels, operator and chaos commands. */
'use strict';

const state = { scene: null, shore: null, truth: null, status: null, ctl: null, connected: false, spawnCount: 0, evidence: null };
let ws = null;
const $ = id => document.getElementById(id);

function hms(t) { t = Math.max(0, Math.floor(t || 0)); const h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = t % 60; return [h, m, s].map(v => String(v).padStart(2, '0')).join(':'); }
function esc(s) { return String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

function connect() {
  try { ws = new WebSocket('ws://localhost:8765/ws'); } catch (e) { setTimeout(connect, 2000); return; }
  ws.onopen = () => { state.connected = true; $('conn').classList.add('ok'); };
  ws.onclose = () => { state.connected = false; $('conn').classList.remove('ok'); setTimeout(connect, 2000); };
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
  ws.onmessage = ev => {
    let f; try { f = JSON.parse(ev.data); } catch (e) { return; }
    if (f.ch === 'scene') { state.scene = f; MapView.setScene(f); buildChaos(); renderStatic(); }
    else if (f.ch === 'shore') state.shore = f;
    else if (f.ch === 'truth') state.truth = f;
    else if (f.ch === 'status') { state.status = f; renderStatus(); if (f.scorecard && !state.scoreShown) { state.scoreShown = true; showScorecard(f.scorecard); } }
    else if (f.ch === 'ctl') onCtl(f);
    renderPanels();
  };
}

function onCtl(f) {
  state.ctl = f;
  if (f.cmd?.cmd === 'reset') { state.scoreShown = false; state.shore = null; state.truth = null; $('modal').style.display = 'none'; }
  if (f.cmd?.cmd === 'evidence') showEvidence(f);
  if (f.cmd?.cmd === 'warp' || f.cmd?.cmd === 'pause' || f.cmd?.cmd === 'resume') renderStatus();
}

/* ---------- top bar ---------- */
function renderStatus() {
  const s = state.status; if (!s) return;
  $('mode').textContent = s.mode; $('seed').textContent = s.seed;
  $('clock').textContent = hms(s.t); $('tsec').textContent = `t=${s.t} s`;
  $('warp').textContent = `${s.speed}× ${s.auto ? 'auto' : 'manual'}${s.paused ? ' · PAUSED' : ''}`;
  $('btnPause').textContent = s.paused ? 'Resume' : 'Pause';
  document.querySelectorAll('[data-warp]').forEach(b => b.classList.toggle('active', s.auto ? b.dataset.warp === 'auto' : String(s.speed) === b.dataset.warp));
  const ne = s.next_event;
  $('nextev').textContent = ne ? `${ne.kind}${ne.boat ? ' b' + ne.boat : ''}${ne.id ? ' ' + ne.id : ''} in ${ne.t - s.t}s` : 'none';
  const inj = s.injections || [];
  $('injections').textContent = inj.length ? 'injected: ' + inj.slice(-6).map(i => `${i.t}s ${i.kind}${i.boat ? ' b' + i.boat : ''}${i.a !== undefined ? ' ' + i.a + '–' + i.b : ''}${i.action ? ' ' + i.action : ''}`).join(' · ') : 'nothing broken yet';
}

function renderStatic() {
  const S = state.scene; if (!S) return;
  $('rseed').value = S.seed; $('rmode').value = S.mode;
  $('legend').innerHTML = Object.entries(MODE_COLOR).filter(([k]) => k !== 'SHORE').map(([k, c]) => `<span class="dot" style="background:${c}"></span>${k} `).join('') +
    `<br>ribbon: time since a live boat passed within ${S.cfg?.r_verify} m, target ${S.cfg?.revisit_target_s} s (evaluator) · <span style="color:#ff5c5c">◆</span> contact, no AIS · ▲ AIS track (shore) · ✕ link cut / boat failed`;
}

/* ---------- right panels ---------- */
function renderPanels() {
  const S = state.scene, sh = state.shore, tr = state.truth, useTruth = MapView.view === 'truth';
  const t = state.status?.t || 0;
  const boats = useTruth ? (tr?.boats || []) : (sh?.boats || []);
  const tasks = (useTruth ? tr?.tasks : sh?.tasks) || {};
  $('rolesSrc').textContent = useTruth ? 'evaluator' : 'shore picture';
  // roles
  const rb = $('roles').querySelector('tbody'); rb.innerHTML = '';
  for (const b of boats) {
    const tasksTxt = [...(b.tour || []).map(x => x.replace('seg:', '')), b.pick || '', b.relay ? 'relay' : '', b.shadow ? 'shadow ' + b.shadow.replace('contact:', '') : '', b.hold ? 'hold' : '', b.cue ? 'cue' : ''].filter(Boolean).join(', ') || '—';
    const link = useTruth ? `${b.path} (${Math.round((b.shore_age || 0) / 1000)}s)` : `${b.link} (${b.age_s}s)`;
    const col = MODE_COLOR[b.mode] || '#4ea1ff';
    const tr_ = document.createElement('tr');
    tr_.innerHTML = `<td>${String(b.id).padStart(2, '0')}${b.failed ? ' ✕' : ''}</td><td><span class="mode" style="background:${col}">${esc(b.mode)}</span></td><td>${esc(tasksTxt)}</td><td>${Math.round((b.batt || 0) / 10)}%</td><td style="color:${b.link === 'none' || b.path === 'none' ? '#ff5c5c' : 'inherit'}">${esc(link)}</td>`;
    rb.appendChild(tr_);
  }
  // pickets
  const pk = [];
  for (const k of ['N', 'S']) {
    const r = tasks['pick:' + k];
    if (!r) { pk.push(`picket ${k}: unknown`); continue; }
    if (r.state === 1) pk.push(`<span style="color:#3ddc84">picket ${k}: covered by boat ${r.owner}</span>`);
    else { const ev = (sh?.events || []).filter(e => e.task === 'pick:' + k && e.kind === 'gap').pop(); pk.push(`<span style="color:#ff5c5c">picket ${k}: UNCOVERED${ev ? ' since ' + hms(ev.t / 1000) + ' (' + Math.max(0, t - Math.floor(ev.t / 1000)) + 's)' : ''}</span>`); }
  }
  $('pickets').innerHTML = pk.join('<br>');
  // ages
  if (tr?.seg_age && S) {
    const target = S.cfg?.revisit_target_s || 12000;
    $('ages').innerHTML = Object.entries(tr.seg_age).map(([k, v]) => { const f = Math.min(1, v / target); return `<div class="agerow"><span>${k.replace('seg:', '')}</span><div class="bar"><i style="width:${(f * 100).toFixed(0)}%;background:${MapView.ageColor(v, target)}"></i></div><span class="v">${Math.round(v / 60)} min</span></div>`; }).join('');
    $('agenums').innerHTML = `<span>km overdue <b style="color:${tr.km_overdue > 0 ? '#ff5c5c' : '#3ddc84'}">${tr.km_overdue}</b></span><span>worst age <b>${Math.round(tr.worst_age_s / 60)} min</b></span><span>crossings in view <b>${tr.crossings_in_view}/${tr.crossings}</b></span>`;
  }
  // cards
  const cards = sh?.cards || [];
  $('actions').textContent = `${sh?.actions || 0} operator actions`;
  if (!cards.length) $('cards').innerHTML = '<span style="color:var(--muted)">No pending decisions. Watching is pre-approved; everything beyond watching waits for a person.</span>';
  else $('cards').innerHTML = cards.map(c => `<div class="card ${c.tier === 'held' ? 'held' : ''}"><div class="tier">${esc(c.tier)} · ${hms(c.t / 1000)}</div><div class="title">${esc(c.title)}</div><div class="text">${esc(c.text)}</div><div class="btns">${(c.options || []).map(o => `<button data-card="${esc(c.id)}" data-cid="${esc(c.cid || c.id)}" data-action="${o.toLowerCase()}" class="${o === 'Stop' || o === 'Decline' ? 'danger' : 'good'}">${esc(o)}</button>`).join('')}</div>${c.tier === 'held' ? '<div class="wait">No answer yet: boat keeps watching.</div>' : ''}</div>`).join('');
  // tasks
  const tb = $('tasks').querySelector('tbody'); tb.innerHTML = '';
  const order = k => ({ relay: 0, contact: 1, cue: 2, seg: 3, pick: 4 }[k.split(':')[0]] ?? 9);
  for (const k of Object.keys(tasks).sort((a, b) => order(a) - order(b) || a.localeCompare(b))) {
    const r = tasks[k]; const kind = k.split(':')[0];
    if (kind === 'cue' && r.state === 2) continue;
    const st = r.state === 0 ? 'open' : r.state === 1 ? 'claimed' : (kind === 'contact' || kind === 'cue') ? 'closed' : 'vetoed';
    const gap = r.state !== 1 && (kind === 'seg' || kind === 'pick');
    let since = '';
    if (gap) { const ev = (sh?.events || []).filter(e => e.task === k && e.kind === 'gap').pop(); if (ev) since = ` ${Math.max(0, t - Math.floor(ev.t / 1000))}s`; }
    const row = document.createElement('tr'); if (gap) row.className = 'gap';
    row.innerHTML = `<td>${esc(k)}</td><td>${r.owner || '—'}</td><td>${r.v}</td><td>${r.deputy || '—'}</td><td>${gap ? 'GAP' + since : st}</td>`;
    tb.appendChild(row);
  }
  // events
  const evs = (sh?.events || []).slice().reverse();
  const html = evs.map(e => `<div class="ev-${esc(e.kind)}"><span class="t">${hms(e.t / 1000)}</span>${esc(e.text)}</div>`).join('');
  if ($('events').innerHTML !== html) $('events').innerHTML = html;
}

/* ---------- chaos controls ---------- */
function buildChaos() {
  const ids = [1, 2, 3, 4, 5];
  $('killgrp').innerHTML = ids.map(i => `<button class="danger" data-kill="${i}">Kill ${i}</button>`).join('') + ids.map(i => `<button class="good" data-restore="${i}">R${i}</button>`).join('');
  const opts = ['shore', ...ids].map(v => `<option value="${v}">${v}</option>`).join('');
  $('linkA').innerHTML = ids.map(v => `<option value="${v}">${v}</option>`).join(''); $('linkA').value = '4';
  $('linkB').innerHTML = opts; $('linkB').value = 'shore';
  $('battBoat').innerHTML = ids.map(v => `<option value="${v}">${v}</option>`).join('');
}

function toggleKill(i) {
  const failed = new Set(state.truth?.failed || []);
  send({ cmd: 'inject', kind: failed.has(i) ? 'boat_restore' : 'boat_fail', boat: i });
}

document.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.kill) send({ cmd: 'inject', kind: 'boat_fail', boat: +b.dataset.kill });
  else if (b.dataset.restore) send({ cmd: 'inject', kind: 'boat_restore', boat: +b.dataset.restore });
  else if (b.dataset.warp) send({ cmd: 'warp', speed: b.dataset.warp === 'auto' ? 'auto' : +b.dataset.warp });
  else if (b.dataset.action) send({ cmd: 'operator', action: b.dataset.action, cid: b.dataset.cid });
});
$('btnPause').onclick = () => send({ cmd: state.status?.paused ? 'resume' : 'pause' });
$('btnReset').onclick = () => send({ cmd: 'reset', mode: $('rmode').value, seed: +$('rseed').value });
$('btnCut').onclick = () => send({ cmd: 'inject', kind: 'link_off', a: $('linkA').value, b: $('linkB').value });
$('btnLinkOn').onclick = () => send({ cmd: 'inject', kind: 'link_on', a: $('linkA').value, b: $('linkB').value });
$('btnBatt').onclick = () => send({ cmd: 'inject', kind: 'battery_low', boat: +$('battBoat').value });
$('btnSpawn').onclick = () => { MapView.spawnMode = !MapView.spawnMode; $('btnSpawn').classList.toggle('active', MapView.spawnMode); };
$('btnScore').onclick = () => showScorecard(state.status?.scorecard);
$('btnEvidence').onclick = () => { showScorecard(state.status?.scorecard); send({ cmd: 'evidence', tamper: 3 }); };
$('btnEvidence2').onclick = () => send({ cmd: 'evidence', tamper: 3 });
$('btnClose').onclick = () => { $('modal').style.display = 'none'; };
$('tabShore').onclick = () => setView('shore');
$('tabTruth').onclick = () => setView('truth');

function setView(v) {
  MapView.view = v;
  $('tabShore').classList.toggle('active', v === 'shore'); $('tabTruth').classList.toggle('active', v === 'truth');
  $('banner').style.display = v === 'truth' ? 'block' : 'none';
  renderPanels();
}

MapView.onClick = (xy) => {
  if (!MapView.spawnMode) return;
  state.spawnCount++;
  send({ cmd: 'inject', kind: 'contact_start', id: 'C-judge-' + state.spawnCount, x: Math.round(xy[0]), y: Math.round(xy[1]), ais: false, sog_kn: 0.4, class: 'dusk' });
  MapView.spawnMode = false; $('btnSpawn').classList.remove('active');
};

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.key === ' ') { e.preventDefault(); $('btnPause').click(); }
  else if (/^[1-5]$/.test(e.key)) toggleKill(+e.key);
  else if (e.key === 'r') { const cut = (state.truth?.cut || []).some(([a, b]) => (a === 0 && b === 5) || (a === 5 && b === 0)); send({ cmd: 'inject', kind: cut ? 'link_on' : 'link_off', a: 5, b: 'shore' }); }
  else if (e.key === 'a') send({ cmd: 'warp', speed: 'auto' });
  else if (e.key === 's') setView('shore');
  else if (e.key === 't') setView('truth');
});

/* ---------- scorecard and evidence ---------- */
function showScorecard(sc) {
  $('modal').style.display = 'flex';
  $('modalTitle').textContent = sc ? `Scorecard — ${sc.mode}, seed ${sc.seed}, t=${sc.t_s}s` : 'Scorecard';
  if (!sc) { $('modalBody').innerHTML = '<span style="color:var(--muted)">Not evaluated yet (evaluate event at ' + (state.scene?.cfg?.evaluate_s ?? '?') + ' s).</span>'; return; }
  const rows = [
    ['Cable km overdue at end (headline)', `${sc.cable_km_overdue} of ${sc.cable_km_total} km`],
    ['Lane crossings in view after T (cost)', `${sc.lane_crossings_in_view} / ${sc.lane_crossings_post_event}`],
    ['Worst revisit age', `${sc.worst_age_s} s (${Math.round(sc.worst_age_s / 60)} min)`],
    ['Event to all cable segments owned', sc.time_to_all_segs_owned_s == null ? 'never' : sc.time_to_all_segs_owned_s + ' s'],
    ['Loiter start to detection', Object.entries(sc.detect_s || {}).map(([k, v]) => `${k}: ${v} s`).join(', ') || 'not detected'],
    ['Loiter start to shadow in view', Object.entries(sc.in_view_s || {}).map(([k, v]) => `${k}: ${v} s`).join(', ') || '—'],
    ['Operator actions', `${sc.operator_actions} (${sc.operator_actions_per_hour}/h)`],
    ['Reports queued offline', sc.reports_queued],
    ['Repair claims after T', sc.repair_claims_after_T],
    ['Radio', `${sc.radio?.sent} sent, ${sc.radio?.dropped} dropped by the tape, ${sc.radio?.delivered} delivered`],
    ['Hashes', sc.final_hash ? `warm ${sc.warm_hash} · ages T−1 ${sc.ages_T_minus_1} · final ${sc.final_hash}` : 'live run (hashes are logged in batch runs)'],
  ];
  $('modalBody').innerHTML = '<table>' + rows.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('') + '</table>';
  $('evidence').textContent = '';
}

function showEvidence(f) {
  $('modal').style.display = 'flex';
  let txt = (f.lines || []).join('\n') + `\n\nIntact bundle: ${f.verified ? 'VERIFIED' : 'TAMPERED'}`;
  if (f.tampered) txt += `\n\nCopy with one edited line (boat 3, seq ${f.tampered.edited_seq}):\n` + f.tampered.lines.join('\n') + `\n=> ${f.tampered.ok ? 'VERIFIED (should not happen)' : 'TAMPERED, first bad sequence named above'}`;
  $('evidence').textContent = txt;
}

/* ---------- boot ---------- */
MapView.init($('map'));
connect();
(function frame() {
  MapView.draw(state);
  const tip = $('tooltip');
  if (MapView.hover) { tip.style.display = 'block'; tip.textContent = MapView.hover.text; tip.style.left = (MapView.hover.x + 14) + 'px'; tip.style.top = (MapView.hover.y + 14) + 'px'; }
  else tip.style.display = 'none';
  requestAnimationFrame(frame);
})();
