/* map.js — projection and Canvas drawing for the Great Belt box. No libraries, no tiles. */
'use strict';

const MODE_COLOR = { PATROL: '#4ea1ff', RELAY: '#b388ff', SHADOWING: '#ff9f43', HOLDING: '#ffd166',
  RETURNING: '#7b8794', UNAVAILABLE: '#3a4350', CUE: '#2ec4b6', SHORE: '#ffffff' };

const MapView = {
  canvas: null, ctx: null, scene: null, view: 'shore', hover: null, spawnMode: false,
  W: 0, H: 0, scale: 1, ox: 0, oy: 0, sinB: 0, cosB: 1, sinV: 0, cosV: 1, onClick: null,

  init(canvas) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    const ro = new ResizeObserver(() => this.resize());
    ro.observe(canvas.parentElement);
    this.resize();
    canvas.addEventListener('mousemove', e => this.onMove(e));
    canvas.addEventListener('mouseleave', () => { this.hover = null; });
    canvas.addEventListener('click', e => { if (this.onClick) this.onClick(this.canvasToXY(e.offsetX, e.offsetY), e); });
  },

  resize() {
    const p = this.canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    this.W = p.clientWidth; this.H = p.clientHeight;
    this.canvas.width = this.W * dpr; this.canvas.height = this.H * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.fit();
  },

  setScene(scene) {
    this.scene = scene;
    const b = scene.bearing * Math.PI / 180;
    this.sinB = Math.sin(b); this.cosB = Math.cos(b);
    this.sinV = Math.sin(b + Math.PI / 2); this.cosV = Math.cos(b + Math.PI / 2);
    this.fit();
  },

  fit() {
    if (!this.scene) return;
    const margin = 40;
    const sx = (this.W - 2 * margin) / this.scene.len_m;
    const sy = (this.H - 2 * margin) / this.scene.wid_m;
    this.scale = Math.min(sx, sy);
    this.ox = this.W / 2; this.oy = this.H / 2;
  },

  // xy (metres, x east, y north) -> box frame uv -> canvas px
  toUV(x, y) {
    const dx = x - this.scene.center[0], dy = y - this.scene.center[1];
    return [dx * this.sinB + dy * this.cosB, dx * this.sinV + dy * this.cosV];
  },
  px(x, y) {
    const [u, v] = this.toUV(x, y);
    return [this.ox + u * this.scale, this.oy - v * this.scale]; // +v (WSW) drawn upward
  },
  canvasToXY(cx, cy) {
    const u = (cx - this.ox) / this.scale, v = -(cy - this.oy) / this.scale;
    const x = this.scene.center[0] + u * this.sinB + v * this.sinV;
    const y = this.scene.center[1] + u * this.cosB + v * this.cosV;
    return [x, y];
  },
  m(px) { return px * this.scale; },

  onMove(e) {
    this.mouse = [e.offsetX, e.offsetY];
  },

  ageColor(ageS, target) {
    const f = Math.max(0, Math.min(1, ageS / Math.max(1, target)));
    // green -> yellow -> red
    const r = f < 0.5 ? Math.round(2 * f * 255) : 255;
    const g = f < 0.5 ? 220 : Math.round(220 * (1 - (f - 0.5) * 2));
    return `rgb(${r},${g},60)`;
  },

  draw(state) {
    const ctx = this.ctx, S = this.scene;
    ctx.clearRect(0, 0, this.W, this.H);
    if (!S) { ctx.fillStyle = '#8a97a8'; ctx.font = '14px system-ui'; ctx.fillText('Waiting for the bridge on ws://localhost:8765/ws …', 20, 30); return; }
    const truth = state.truth || {}, shore = state.shore || {};
    const useTruth = this.view === 'truth';
    const hoverables = [];

    // box
    ctx.strokeStyle = '#3a4a5c'; ctx.lineWidth = 1.2;
    ctx.beginPath(); S.box.forEach((c, i) => { const [x, y] = this.px(c[0], c[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.closePath(); ctx.stroke();

    // lane band
    if (S.lane_p5 && S.lane_p95 && S.lane_p5.length) {
      ctx.fillStyle = 'rgba(120,150,190,0.10)';
      ctx.beginPath();
      S.lane_p5.forEach((p, i) => { const [x, y] = this.px(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
      for (let i = S.lane_p95.length - 1; i >= 0; i--) { const [x, y] = this.px(S.lane_p95[i][0], S.lane_p95[i][1]); ctx.lineTo(x, y); }
      ctx.closePath(); ctx.fill();
    }
    this.polyline(S.lane, 'rgba(140,170,210,0.45)', 1, [6, 4]);

    // cables
    for (const [name, pieces] of Object.entries(S.cables || {})) {
      const strong = (S.scenario_lines || []).includes(name);
      pieces.forEach(p => this.polyline(p, strong ? '#5d6c80' : '#2e3a48', strong ? 2 : 1));
    }

    // freshness ribbon (evaluator)
    const ages = truth.ages_s, target = S.cfg?.revisit_target_s || 12000;
    if (ages && S.segments) {
      let k = 0;
      ctx.lineCap = 'round';
      for (const seg of S.segments) {
        for (let i = 0; i < seg.samples.length; i++, k++) {
          const a = ages[k]; if (a === undefined) continue;
          const [x, y] = this.px(seg.samples[i][0], seg.samples[i][1]);
          ctx.fillStyle = this.ageColor(a, target);
          ctx.beginPath(); ctx.arc(x, y, Math.max(1.6, this.m(45)), 0, Math.PI * 2); ctx.fill();
        }
      }
      // segment labels
      ctx.fillStyle = '#9fb0c4'; ctx.font = '10px system-ui';
      for (const seg of S.segments) {
        const mid = seg.samples[Math.floor(seg.samples.length / 2)];
        const [x, y] = this.px(mid[0], mid[1]);
        ctx.fillText(seg.task.replace('seg:', ''), x + 4, y - 4);
      }
    }

    // stations
    const tasks = (useTruth ? truth.tasks : shore.tasks) || {};
    this.station(S.relay, '#b388ff', 'relay station', tasks.relay?.state === 1 ? 'filled' : 'hollow');
    for (const [k, p] of Object.entries(S.pickets || {})) {
      const open = tasks['pick:' + k] ? tasks['pick:' + k].state !== 1 : false;
      this.station(p, open ? '#ff5c5c' : '#3ddc84', 'picket ' + k + (open ? ' OPEN' : ''), open ? 'hollow' : 'filled');
    }
    this.shoreMarker(S.shore);

    // cut links & radio links (truth only, but cut links also matter in shore view as "link lost")
    const nodes = {};
    (truth.boats || []).forEach(b => nodes[b.id] = [b.x, b.y]);
    nodes[0] = S.shore;
    if (useTruth && truth.links) {
      ctx.strokeStyle = 'rgba(78,161,255,0.25)'; ctx.lineWidth = 1; ctx.setLineDash([]);
      for (const [a, b] of truth.links) { if (!nodes[a] || !nodes[b]) continue; const p = this.pxc(nodes[a]), q = this.pxc(nodes[b]); ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke(); }
    }
    for (const [a, b] of (truth.cut || [])) {
      if (!nodes[a] || !nodes[b]) continue;
      const p = this.pxc(nodes[a]), q = this.pxc(nodes[b]);
      ctx.strokeStyle = '#ff5c5c'; ctx.lineWidth = 1.2; ctx.setLineDash([5, 5]);
      ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke(); ctx.setLineDash([]);
      const mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2; this.cross(mx, my, 6, '#ff5c5c');
    }

    // AIS tracks (shore picture)
    for (const a of (shore.ais || [])) {
      const [x, y] = this.px(a.x, a.y); const alpha = Math.max(0.15, 1 - (a.age_s || 0) / 600);
      ctx.save(); ctx.translate(x, y); ctx.rotate((a.cog || 0) * Math.PI / 180);
      ctx.fillStyle = `rgba(170,180,195,${alpha})`; ctx.beginPath(); ctx.moveTo(0, -6); ctx.lineTo(4, 5); ctx.lineTo(-4, 5); ctx.closePath(); ctx.fill(); ctx.restore();
      hoverables.push({ x, y, r: 7, text: `AIS ${a.track}\ntype ${a.type}  sog ${a.sog} kn  cog ${a.cog}\nage ${a.age_s}s` });
    }

    // cues (shore)
    for (const [task, g] of Object.entries(shore.cues || {})) {
      const st = tasks[task]?.state; if (st === 2) continue;
      const [x, y] = this.px(g.x, g.y);
      ctx.strokeStyle = '#2ec4b6'; ctx.lineWidth = 1.2; ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = '#2ec4b6'; ctx.font = '10px system-ui'; ctx.fillText('cue for a look', x + 11, y + 3);
    }

    // contacts (shore) / vessels (truth)
    if (useTruth) {
      for (const v of (truth.vessels || [])) {
        const [x, y] = this.px(v.x, v.y); this.diamond(x, y, 7, '#ff5c5c');
        ctx.fillStyle = '#ff8c8c'; ctx.font = '11px system-ui'; ctx.fillText(v.id + (v.ais ? '' : ' (no AIS)'), x + 10, y + 4);
        hoverables.push({ x, y, r: 9, text: `vessel ${v.id} (synthetic)\nsog ${v.sog_kn} kn  course ${v.course}\nAIS ${v.ais ? 'on' : 'off'}  class ${v.cls}` });
      }
    }
    for (const c of (shore.contacts || [])) {
      if (c.state === 2 && !useTruth) continue;
      const [x, y] = this.px(c.x, c.y);
      const col = c.state === 2 ? '#7b8794' : '#ff5c5c';
      this.diamond(x, y, 7, col);
      ctx.strokeStyle = col; ctx.lineWidth = 1; ctx.setLineDash([2, 4]);
      ctx.beginPath(); ctx.arc(x, y, this.m(S.cfg?.standoff || 1852), 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = col; ctx.font = '11px system-ui';
      const lab = `${c.id.replace('contact:', '')} · no AIS · ${c.age_s}s ago by boat ${c.by}` + (c.name_read ? ' · NAME READ' : ' · name NOT READ') + (c.anchor_seen ? ' · anchor SEEN' : '');
      ctx.fillText(lab, x + 10, y - 8);
      hoverables.push({ x, y, r: 9, text: `${c.id}\nlast obs by boat ${c.by}, ${c.age_s}s ago\nsog ${c.sog} m/s  in view ${c.in_view}\nname read ${c.name_read}  anchor seen ${c.anchor_seen}\nstate ${['open', 'claimed', 'closed'][c.state] ?? c.state}` });
    }

    // boats
    const boats = useTruth ? (truth.boats || []) : (shore.boats || []);
    const failed = new Set(truth.failed || []);
    for (const b of boats) {
      const [x, y] = this.px(b.x, b.y);
      const col = MODE_COLOR[b.mode] || '#4ea1ff';
      const stale = !useTruth && (b.age_s || 0) > 20;
      if (useTruth && b.mode === 'SHADOWING') { ctx.strokeStyle = 'rgba(255,159,67,0.5)'; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.arc(x, y, this.m(S.cfg?.keep_in_view || 2000), 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]); }
      ctx.strokeStyle = 'rgba(78,161,255,0.12)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(x, y, this.m(S.cfg?.r_detect?.dusk || 2000), 0, Math.PI * 2); ctx.stroke();
      if (useTruth && b.target) { const [tx, ty] = this.px(b.target[0], b.target[1]); const ang = Math.atan2(ty - y, tx - x); ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(ang) * 16, y + Math.sin(ang) * 16); ctx.stroke(); }
      // battery arc
      ctx.strokeStyle = (b.batt || 0) < 200 ? '#ff5c5c' : '#3ddc84'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, y, 12, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ((b.batt || 0) / 1000)); ctx.stroke();
      ctx.fillStyle = stale ? '#3a4350' : col; ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#0f141a'; ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'center'; ctx.fillText(String(b.id).padStart(2, '0'), x, y + 4); ctx.textAlign = 'left';
      if (failed.has(b.id) || b.failed) this.cross(x, y, 12, '#ff5c5c');
      if (!useTruth) {
        if (b.link === 'none') this.cross(x + 16, y - 12, 5, '#ff5c5c');
        else if (b.link === 'relay') { ctx.strokeStyle = '#b388ff'; ctx.setLineDash([2, 2]); ctx.beginPath(); ctx.arc(x, y, 15, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]); }
      } else if (b.path === 'none' || (b.shore_age || 0) > 30000) this.cross(x + 16, y - 12, 5, '#ff5c5c');
      ctx.fillStyle = '#d7dee8'; ctx.font = '10px system-ui';
      let lab = b.mode + (b.relay ? ' relay' : '') + (b.pick ? ' ' + b.pick : '');
      if (!useTruth && stale) lab += ` (${b.age_s}s old)`;
      ctx.fillText(lab, x + 14, y + 14);
      hoverables.push({ x, y, r: 13, text: this.boatText(b, useTruth) });
    }

    // north arrow
    this.northArrow();

    // hover
    this.hover = null;
    if (this.mouse) {
      let best = null;
      for (const h of hoverables) { const d = Math.hypot(h.x - this.mouse[0], h.y - this.mouse[1]); if (d <= h.r + 3 && (!best || d < best.d)) best = { d, h }; }
      if (best) this.hover = { x: best.h.x, y: best.h.y, text: best.h.text };
    }
    if (this.spawnMode) { ctx.fillStyle = '#ff5c5c'; ctx.font = '13px system-ui'; ctx.fillText('Click on the map to place a synthetic dark contact', this.W / 2 - 150, this.H - 14); }
  },

  boatText(b, truth) {
    const lines = [`boat ${b.id}  ${b.mode}`, `battery ${((b.batt || 0) / 10).toFixed(0)}%`];
    if (b.tour && b.tour.length) lines.push(`tour ${b.tour.join(' > ')}`);
    if (b.pick) lines.push(`picket ${b.pick}`);
    if (b.relay) lines.push('role: relay');
    if (truth) { lines.push(`shore age ${Math.round((b.shore_age || 0) / 1000)}s  path ${b.path}  cycle ${b.cycle_s}s`); if (b.shadow) lines.push(`shadowing ${b.shadow}`); if (b.hold) lines.push(`holding ${b.hold}`); if (b.cue) lines.push(`cue ${b.cue}`); if (b.failed) lines.push('FAILED'); if (b.docked) lines.push('docked'); }
    else lines.push(`link ${b.link}  via ${b.via}  last heard ${b.age_s}s ago`);
    return lines.join('\n');
  },

  polyline(pts, color, width, dash) {
    if (!pts || pts.length < 2) return;
    const ctx = this.ctx; ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash || []);
    ctx.beginPath(); pts.forEach((p, i) => { const [x, y] = this.px(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke(); ctx.setLineDash([]);
  },
  pxc(p) { return this.px(p[0], p[1]); },
  station(p, color, label, style) {
    if (!p) return; const ctx = this.ctx; const [x, y] = this.px(p[0], p[1]);
    ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.rect(x - 5, y - 5, 10, 10); ctx.stroke();
    if (style === 'filled') { ctx.fillStyle = color; ctx.fill(); }
    ctx.fillStyle = color; ctx.font = '10px system-ui'; ctx.fillText(label, x + 8, y - 6);
  },
  shoreMarker(p) {
    if (!p) return; const ctx = this.ctx; let [x, y] = this.px(p[0], p[1]);
    const cx = Math.max(14, Math.min(this.W - 14, x)), cy = Math.max(14, Math.min(this.H - 14, y));
    if (cx !== x || cy !== y) { ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + (x - cx) * 0.3, cy + (y - cy) * 0.3); ctx.stroke(); }
    ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.moveTo(cx, cy - 7); ctx.lineTo(cx + 6, cy + 5); ctx.lineTo(cx - 6, cy + 5); ctx.closePath(); ctx.fill();
    ctx.font = '11px system-ui'; ctx.fillText('Korsør, shore' + ((cx !== x || cy !== y) ? ' (off box, 3 km east)' : ''), cx - 40, cy + 18);
  },
  diamond(x, y, r, color) { const ctx = this.ctx; ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath(); ctx.fill(); },
  cross(x, y, r, color) { const ctx = this.ctx; ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x - r, y - r); ctx.lineTo(x + r, y + r); ctx.moveTo(x + r, y - r); ctx.lineTo(x - r, y + r); ctx.stroke(); },
  northArrow() {
    const ctx = this.ctx; const x = this.W - 40, y = 60;
    // north in canvas: direction of +y (north) through the projection
    const [ax, ay] = this.px(this.scene.center[0], this.scene.center[1]);
    const [bx, by] = this.px(this.scene.center[0], this.scene.center[1] + 1000);
    const ang = Math.atan2(by - ay, bx - ax);
    ctx.strokeStyle = '#9fb0c4'; ctx.fillStyle = '#9fb0c4'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(ang) * 22, y + Math.sin(ang) * 22); ctx.stroke();
    ctx.font = 'bold 11px system-ui'; ctx.fillText('N', x + Math.cos(ang) * 30 - 4, y + Math.sin(ang) * 30 + 4);
    ctx.font = '10px system-ui'; ctx.fillText('1 km', x - 50, this.H - 30);
    ctx.beginPath(); ctx.moveTo(x - 52, this.H - 24); ctx.lineTo(x - 52 + this.m(1000), this.H - 24); ctx.stroke();
  },
};
