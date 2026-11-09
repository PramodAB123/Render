// Automatic shot list for the stick-figure engine of claude-animation-skills (MIT, by Artem Novitckii).
// The original engine expects shots written by hand for every reel; this file builds them from the story
// timeline (window.STICK, written by pipeline/stick.py), using the engine's own rig (drawStick, faces, poses)
// and props (sky, sun, clouds, sea, ships, barrels, crates, chest, lantern, burst, puff, sweat, sparkle).
const D = window.STICK; const CAST = D.cast;
const C = (base, extra) => Object.assign({}, base, extra);
const walkLegs = (t, sp = 9, amp = .55) => ({ L: [Math.sin(t * sp) * amp + .05, -Math.max(0, Math.sin(t * sp + 1)) * .7], R: [-Math.sin(t * sp) * amp + .05, -Math.max(0, -Math.sin(t * sp + 1)) * .7] });
const walkArms = (t, sp = 9, amp = .6) => ({ L: [.3 - Math.sin(t * sp) * amp, -.3], R: [.3 + Math.sin(t * sp) * amp, -.3] });
const handheld = (t, a = 4) => shake(t * .35, a, 1, 2);
const SKIES = { day: ['#3ea6ee', '#c9ecfb'], dusk: ['#6b4fb0', '#f6a66b'], night: ['#0d1440', '#3a3f7a'], dawn: ['#7aa0e0', '#ffd2a8'] };
const GROUND = { grass: ['#6cc24a', '#4f9a35'], sand: ['#f0cf7a', '#d9ad55'], snow: ['#f4f7fb', '#d5dde8'], road: ['#8a8f99', '#6c707a'], floor: ['#c98d55', '#a06a3a'] };

function face(mood, talking, t, blinkSeed = 0) {
  const blink = ((t + blinkSeed) % 3.3) < .1 ? 1 : 0;
  const m = { calm: { eyes: 'normal', mouth: 'smile' }, happy: { eyes: 'happy', mouth: 'grin' }, scared: { eyes: 'wide', mouth: 'o', browUp: 1 },
    shocked: { eyes: 'wide', mouth: 'o', browUp: 1.4 }, angry: { eyes: 'normal', mouth: 'teeth', browAng: -.35 }, sad: { eyes: 'normal', mouth: 'frown', browAng: .3, look: [0, .5] },
    smug: { eyes: 'smug', mouth: 'smirk', browOne: 1 }, dizzy: { eyes: 'spiral', mouth: 'flat' }, think: { eyes: 'normal', mouth: 'flat', look: [.6, -.6], browOne: -1 } }[mood] || { eyes: 'normal', mouth: 'smile' };
  const f = Object.assign({ blink }, m);
  if (talking && mood != 'dizzy') f.mouth = Math.sin(t * 17) > -.1 ? (mood == 'happy' ? 'grin' : 'o') : (m.mouth == 'o' ? 'flat' : m.mouth);
  return f;
}
function talkingAt(s, t) { return (s.words || []).some(w => t >= w.s && t <= w.e + .05); }
function hills(ctx, base, col, seed, amp = 120) { const R = rng(seed); const pts = [[-600, 2600]]; for (let x = -600; x <= 1700; x += 140) pts.push([x, base - R() * amp]); pts.push([1700, 2600]); path(ctx, pts); fillStroke(ctx, col, 6); }
function bg(ctx, t, cam, s, o = {}) {
  const tod = s.tod || 'day', sky = SKIES[tod] || SKIES.day, gr = GROUND[s.ground] || GROUND.grass;
  applyCam(ctx, cam, .08); drawSky(ctx, sky[0], sky[1]);
  if (tod == 'night') { const R = rng(9); ctx.fillStyle = '#fff'; for (let i = 0; i < 60; i++) { circle(ctx, R() * 1300 - 100, R() * 700 - 200, 2 + R() * 3); ctx.fill(); } circle(ctx, 860, 180, 70); fillStroke(ctx, '#f6f1d0', 6); }
  else { applyCam(ctx, cam, .1); drawSun(ctx, 860, 200, 80, t, tod == 'dusk' ? .6 : 1); }
  applyCam(ctx, cam, .14); if (tod != 'night') { drawCloud(ctx, 160 + t * 6, 300, 120, 1); drawCloud(ctx, 760 + t * 4, 170, 90, 2); drawCloud(ctx, -100 + t * 5, 520, 80, 4, .9); }
  if (s.ground == 'sea') { applyCam(ctx, cam, .45); drawSea(ctx, 900, t); if (o.ship !== false) drawShip(ctx, 760, 960, .55, t, { flag: '#1b1820', hull: '#5a3a2a' }); applyCam(ctx, cam, 1); return; }
  applyCam(ctx, cam, .3); hills(ctx, 1000, mix(gr[0], '#2a3f6a', tod == 'night' ? .55 : .25), 3, 160);
  applyCam(ctx, cam, .6); hills(ctx, 1150, mix(gr[0], '#000', tod == 'night' ? .45 : .05), 7, 70);
  applyCam(ctx, cam, 1); rrect(ctx, -700, 1300, 2500, 1400, 0); fillStroke(ctx, mix(gr[1], '#000', tod == 'night' ? .45 : 0), 6);
  if (s.ground == 'road') { ctx.fillStyle = '#f2d65c'; for (let x = -600 + ((-t * 300) % 240); x < 1700; x += 240) ctx.fillRect(x, 1560, 120, 18); }
}
function nightTint(ctx, s) { if ((s.tod || 'day') == 'night') darkness(ctx, .18, '#0a0c30'); }
const cast = i => CAST[i % CAST.length];
const SETUPS = {
  closeup(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 900 + hh[1] - lt * 10, z: 1 + lt * .035, r: Math.sin(t * .5) * .006 };
    ctx.save(); ctx.filter = 'blur(5px)'; bg(ctx, t, cam, s); ctx.restore(); applyCam(ctx, cam, 1);
    stickA(ctx, C(cast(s.who), { x: 540, y: 2050, s: 1500, bob: Math.sin(t * 3) * .004, headTilt: Math.sin(t * 1.6) * .03, shadow: false, face: face(s.mood, talkingAt(s, t), t), arms: { L: [.25, -.1], R: [.25, -.1] } }));
    if (s.mood == 'scared' || s.mood == 'shocked') sweat(ctx, 760, 900, 60, clamp(lt * 3)); nightTint(ctx, s); },
  talk(ctx, lt, t, s) { const hh = handheld(t, 4), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.02 + lt * .02 };
    bg(ctx, t, cam, s); applyCam(ctx, cam, 1); const a = cast(s.who), b = cast(s.who + 1), tk = talkingAt(s, t);
    stickA(ctx, C(a, { x: 330, y: 1420, s: 520, bob: Math.sin(t * 4) * .006, face: face(s.mood, tk, t), arms: tk ? { L: [.3, -.1], R: [1.2 + Math.sin(t * 5) * .2, -.6] } : POSE.idle.arms }));
    stickA(ctx, C(b, { x: 780, y: 1440, s: 470, flip: -1, bob: Math.sin(t * 4 + 1) * .006, face: face(s.other_mood || 'calm', false, t, 1.3), arms: POSE.idle.arms })); nightTint(ctx, s); },
  walk(ctx, lt, t, s) { const cam = { x: 540 + lt * 30, y: 960, z: 1.04 }; const sv = Object.assign({}, s); bg(ctx, t * 1.6, cam, sv); applyCam(ctx, cam, 1);
    for (let i = 0; i < 4; i++) drawBarrel(ctx, ((i * 520 - lt * 260) % 2080 + 2080) % 2080 - 300, 1400, .9);
    stickA(ctx, C(cast(s.who), { x: 420 + lt * 30, y: 1430, s: 520, legs: walkLegs(t), arms: walkArms(t), lean: .06, bob: Math.abs(Math.sin(t * 9)) * .01, face: face(s.mood, talkingAt(s, t), t) })); nightTint(ctx, s); },
  run(ctx, lt, t, s) { const cam = { x: 540 + lt * 60, y: 960 + Math.sin(t * 18) * 6, z: 1.05 }; bg(ctx, t * 3, cam, s); applyCam(ctx, cam, 1);
    stickA(ctx, C(cast(s.who), { x: 400 + lt * 60, y: 1430, s: 520, legs: walkLegs(t, 16, .9), arms: walkArms(t, 16, 1.1), lean: .18, bob: Math.abs(Math.sin(t * 16)) * .02, face: face(s.mood || 'scared', false, t) }));
    puff(ctx, 300 + lt * 60, 1440, 50, t, '#f3efe6', Math.floor(t * 8), .7); if (s.mood == 'scared') sweat(ctx, 520 + lt * 60, 900, 40, .9); nightTint(ctx, s); },
  crowd(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1 + lt * .03 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    const up = s.mood == 'happy' || s.mood == 'scared' || s.mood == 'shocked';
    [[150, 1380, 330], [930, 1380, 330], [330, 1430, 400], [760, 1440, 400], [540, 1480, 470]].forEach(([x, y, sz], k) =>
      stickA(ctx, C(cast(k), { x, y, s: sz, flip: x > 540 ? -1 : 1, bob: Math.sin(t * 4 + k) * .01, face: face(s.mood, k == 4 && talkingAt(s, t), t, k), arms: up ? { L: [2.5 + Math.sin(t * 6 + k) * .2, .3], R: [2.5 - Math.sin(t * 6 + k) * .2, .3] } : POSE.idle.arms }))); nightTint(ctx, s); },
  object(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.02 + lt * .03 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    const pop = backOut(clamp(lt / .35)); ctx.save(); ctx.translate(720, 1420); ctx.scale(pop, pop); drawCrate(ctx, 0, 0, 420, 330, 0, (s.label || '???').toUpperCase().slice(0, 14)); ctx.restore();
    stickA(ctx, C(cast(s.who), { x: 270, y: 1440, s: 500, face: face(s.mood || 'smug', talkingAt(s, t), t), arms: { L: [.3, -.1], R: [1.55, -.15] } })); nightTint(ctx, s); },
  reveal(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 1000 + hh[1], z: 1.05 + lt * .04 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    const open = easeOut(clamp((lt - .3) / .5)); drawChest(ctx, 680, 1460, 1.5, open);
    stickA(ctx, C(cast(s.who), { x: 300, y: 1460, s: 500, face: face(open > .5 ? 'happy' : 'shocked', talkingAt(s, t), t), arms: open > .5 ? POSE.handsUp.arms : POSE.idle.arms }));
    const sa = kf(lt, [[.6, 0], [.8, 1], [1.4, .2]]); sparkle(ctx, 640, 1150, 90 * sa, sa); sparkle(ctx, 800, 1110, 60 * sa, sa);
    if (s.label) text(ctx, s.label.toUpperCase().slice(0, 16), 680, 1000 - 40 * open, 90 * open, '#ffe14d', INK, 14); },
  night(ctx, lt, t, s) { const cam = { x: 540 + Math.sin(t * .7) * 10, y: 960, z: 1.04 + lt * .03 }; bg(ctx, t, cam, Object.assign({}, s, { tod: 'night' })); applyCam(ctx, cam, 1);
    darkness(ctx, .45); applyCam(ctx, cam, 1); drawLantern(ctx, 760, 1180, 1.6, .8 + Math.sin(t * 9) * .1, t);
    const g = ctx.createRadialGradient(760, 1150, 20, 760, 1150, 700); g.addColorStop(0, 'rgba(255,200,110,.35)'); g.addColorStop(1, 'rgba(255,200,110,0)'); ctx.fillStyle = g; ctx.fillRect(-500, 0, 2500, 2400);
    stickA(ctx, C(cast(s.who), { x: 380, y: 1450, s: 520, face: face(s.mood || 'scared', talkingAt(s, t), t), arms: { L: [.6, -.9], R: [.6, -.9] }, lean: -.05 + Math.sin(t * 30) * .01 }));
    sweat(ctx, 520, 860, 46, .9); },
  impact(ctx, lt, t, s) { const sh = shake(t, 26 * Math.max(0, 1 - lt * 2), 3), cam = { x: 540 + sh[0], y: 960 + sh[1], z: 1.08 - lt * .03 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    const k = easeOut(clamp(lt / .3)); burst(ctx, 650, 930, 330 * k, 12, '#ffd23a', 5); if (s.label) text(ctx, s.label.toUpperCase().slice(0, 10), 650, 930, 120 * k, '#fff', INK, 16);
    puff(ctx, 540, 1460, 140 * k, t, '#f3efe6', 4, 1 - clamp(lt - .6));
    stickA(ctx, C(cast(s.who), { x: 330, y: 1460, s: 500, lean: -.25 * k, face: face('dizzy', false, t), arms: POSE.handsUp.arms }));
    if (lt < .12) darkness(ctx, .5 * (1 - lt / .12), '#fff'); nightTint(ctx, s); },
  sea(ctx, lt, t, s) { const hh = handheld(t, 4), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1 + lt * .03 }; bg(ctx, t, cam, Object.assign({}, s, { ground: 'sea' })); applyCam(ctx, cam, 1);
    stickA(ctx, C(cast(s.who), { x: 760, y: 935, s: 130, face: face(s.mood, false, t) })); nightTint(ctx, s); },
  bigtext(ctx, lt, t, s) { const cam = { x: 540, y: 960, z: 1 + lt * .03 }; applyCam(ctx, cam, .2); drawSky(ctx, D.style.accent, mix(D.style.accent, '#000', .35));
    applyCam(ctx, cam, 1); const k = backOut(clamp(lt / .35)); const word = (s.label || s.hl || '').toUpperCase().slice(0, 12);
    ctx.font = `700 240px Poppins`; const fs = Math.min(240, 240 * 860 / Math.max(1, ctx.measureText(word).width));   // fit inside the safe area
    ctx.save(); ctx.translate(540, 900); ctx.rotate(-.04); ctx.scale(k, k); text(ctx, word, 0, 0, fs, '#fff', INK, Math.max(10, fs * .09)); ctx.restore();
    stickA(ctx, C(cast(s.who), { x: 540, y: 1600, s: 420, face: face(s.mood || 'shocked', talkingAt(s, t), t), arms: POSE.handsUp.arms })); },
  think(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.03 + lt * .03 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    stickA(ctx, C(cast(s.who), { x: 440, y: 1450, s: 560, headTilt: .08, face: face('think', talkingAt(s, t), t), arms: { L: [.3, -.1], R: [.4, -2.6] } }));
    for (let i = 0; i < 3; i++) { const a = clamp((lt - i * .25) * 3); if (a > 0) text(ctx, '?', 660 + i * 90, 760 - i * 70 - Math.sin(t * 3 + i) * 10, 110 * a, '#fff', INK, 12); } nightTint(ctx, s); },
};

// ---------- costumes (drawn on top of the engine's rig: head centre is (x, y - .765*s), radius .19*s) ----------
function accessory(ctx, o) { const a = o.acc; if (!a || a === 'none') return; const s = o.s || 400, hx = o.x, hy = o.y - .765 * s * (o.squash || 1), r = .19 * s, lw = Math.max(3, s * .017);
  ctx.save(); ctx.translate(hx, hy); ctx.rotate(o.headTilt || 0);
  if (a === 'crown') { path(ctx, [[-r * .8, -r * .72], [-r * .8, -r * 1.35], [-r * .4, -r * 1.05], [0, -r * 1.5], [r * .4, -r * 1.05], [r * .8, -r * 1.35], [r * .8, -r * .72]]); fillStroke(ctx, '#f2c230', lw);
    [[-r * .4, -r * .9], [0, -r * .95], [r * .4, -r * .9]].forEach(([x, y], k) => { circle(ctx, x, y, r * .09); fillStroke(ctx, ['#d8312b', '#2f63c9', '#3fa35b'][k], lw * .6); }); }
  else if (a === 'helmet') { ctx.beginPath(); ctx.arc(0, -r * .1, r * 1.08, Math.PI * 1.02, Math.PI * 1.98); ctx.closePath(); fillStroke(ctx, '#9aa3ad', lw);
    rrect(ctx, -r * 1.1, -r * .22, r * 2.2, r * .2, r * .08); fillStroke(ctx, '#7d868f', lw); rrect(ctx, -r * .08, -r * .2, r * .16, r * .55, r * .05); fillStroke(ctx, '#7d868f', lw * .8);
    path(ctx, [[0, -r * 1.15], [-r * .12, -r * 1.6], [r * .3, -r * 1.45]]); fillStroke(ctx, o.plume || '#d8312b', lw * .8); }
  else if (a === 'hood') { ctx.beginPath(); ctx.moveTo(-r * 1.25, r * .9); ctx.quadraticCurveTo(-r * 1.4, -r * 1.5, 0, -r * 1.45); ctx.quadraticCurveTo(r * 1.4, -r * 1.5, r * 1.25, r * .9);
    ctx.quadraticCurveTo(r * 1.05, -r * 1.05, 0, -r * 1.1); ctx.quadraticCurveTo(-r * 1.05, -r * 1.05, -r * 1.25, r * .9); fillStroke(ctx, o.hoodCol || '#2f6b5a', lw); }
  else if (a === 'wizard') { path(ctx, [[-r * 1.2, -r * .7], [r * .2, -r * 2.7], [r * 1.2, -r * .7]]); fillStroke(ctx, '#3a3f9a', lw); ellipse(ctx, 0, -r * .72, r * 1.35, r * .2); fillStroke(ctx, '#2c3080', lw); star5(ctx, r * .05, -r * 1.5, r * .22, 0, '#ffe14d'); }
  else if (a === 'tophat') { rrect(ctx, -r * .62, -r * 1.75, r * 1.24, r * 1.05, r * .06); fillStroke(ctx, '#26262e', lw); rrect(ctx, -r * 1.05, -r * .78, r * 2.1, r * .16, r * .07); fillStroke(ctx, '#26262e', lw); ctx.fillStyle = '#b3202a'; ctx.fillRect(-r * .6, -r * 1.0, r * 1.2, r * .14); }
  else if (a === 'cowboy') { ellipse(ctx, 0, -r * .72, r * 1.55, r * .28); fillStroke(ctx, '#8a5a2b', lw); ctx.beginPath(); ctx.moveTo(-r * .7, -r * .75); ctx.quadraticCurveTo(-r * .75, -r * 1.55, 0, -r * 1.35); ctx.quadraticCurveTo(r * .75, -r * 1.55, r * .7, -r * .75); ctx.closePath(); fillStroke(ctx, '#9b6a35', lw); }
  else if (a === 'turban') { ellipse(ctx, 0, -r * .75, r * 1.08, r * .62); fillStroke(ctx, '#e8a33a', lw); circle(ctx, 0, -r * .95, r * .14); fillStroke(ctx, '#d8312b', lw * .6); }
  else if (a === 'chef') { rrect(ctx, -r * .7, -r * 1.0, r * 1.4, r * .35, r * .05); fillStroke(ctx, '#fff', lw); [-.45, 0, .45].forEach(dx => { circle(ctx, r * dx, -r * 1.35, r * .42); fillStroke(ctx, '#fff', lw); }); }
  else if (a === 'cap') { ctx.beginPath(); ctx.arc(0, -r * .5, r * .98, Math.PI * 1.05, Math.PI * 1.95); ctx.closePath(); fillStroke(ctx, o.capCol || '#2f6b3f', lw); rrect(ctx, r * .1, -r * .62, r * 1.25, r * .16, r * .08); fillStroke(ctx, o.capCol || '#2f6b3f', lw); }
  ctx.restore(); }
// ---------- designed from the script: extras on the face, a cape behind, a prop in hand, build ----------
function extrasFront(ctx, o) { const ex = o.extras || []; if (!ex.length || o.sil) return; const s = o.s || 400, r = .19 * s, lw = Math.max(3, s * .017), f = o.flip || 1;
  ctx.save(); ctx.translate(o.x, o.y - .765 * s * (o.squash || 1)); ctx.rotate(o.headTilt || 0); ctx.scale(f, 1);
  if (ex.includes('hair')) { ctx.fillStyle = '#5a3420'; ctx.strokeStyle = INK; ctx.lineWidth = lw; [-1, 1].forEach(sd => { ctx.beginPath(); ctx.moveTo(sd * r * .7, -r * .65); ctx.quadraticCurveTo(sd * r * 1.35, r * .3, sd * r * 1.05, r * 1.25); ctx.lineTo(sd * r * .8, r * .6); ctx.quadraticCurveTo(sd * r * .95, 0, sd * r * .7, -r * .65); ctx.fill(); ctx.stroke(); }); }
  if (ex.includes('beard')) { ctx.beginPath(); ctx.moveTo(-r * .78, r * .25); ctx.quadraticCurveTo(-r * .7, r * 1.35, 0, r * 1.45); ctx.quadraticCurveTo(r * .7, r * 1.35, r * .78, r * .25); ctx.quadraticCurveTo(0, r * .75, -r * .78, r * .25); fillStroke(ctx, '#6b4a2e', lw); }
  if (ex.includes('mustache')) { [-1, 1].forEach(sd => { ctx.beginPath(); ctx.ellipse(sd * r * .22, r * .42, r * .26, r * .09, sd * .25, 0, 7); fillStroke(ctx, '#3a2818', lw * .6); }); }
  if (ex.includes('glasses')) { ctx.strokeStyle = INK; ctx.lineWidth = lw; [-1, 1].forEach(sd => { ctx.beginPath(); ctx.arc(sd * r * .36, -r * .02, r * .26, 0, 7); ctx.stroke(); }); ctx.beginPath(); ctx.moveTo(-r * .1, -r * .02); ctx.lineTo(r * .1, -r * .02); ctx.stroke(); }
  if (ex.includes('eyepatch')) { ctx.strokeStyle = INK; ctx.lineWidth = lw * .8; ctx.beginPath(); ctx.moveTo(-r * .95, -r * .45); ctx.lineTo(r * .95, r * .15); ctx.stroke(); ctx.beginPath(); ctx.ellipse(r * .36, -r * .02, r * .26, r * .22, 0, 0, 7); ctx.fillStyle = '#16161c'; ctx.fill(); }
  if (ex.includes('scar')) { ctx.strokeStyle = '#b3202a'; ctx.lineWidth = lw * .7; ctx.beginPath(); ctx.moveTo(-r * .55, -r * .4); ctx.lineTo(-r * .2, r * .3); [-.45, -.32].forEach(k => { ctx.moveTo(r * (k - .12), r * (k + .3) * .9); ctx.lineTo(r * (k + .12), r * (k + .3) * .9 - r * .1); }); ctx.stroke(); }
  ctx.restore(); }
function capeBehind(ctx, o) { if (!(o.extras || []).includes('cape') || o.sil) return; const s = o.s || 400, f = o.flip || 1, sw = Math.sin((o._t || 0) * 3) * .02;
  ctx.save(); ctx.translate(o.x, o.y); ctx.scale(s * f, s * (o.squash || 1)); ctx.rotate(o.lean || 0);
  ctx.beginPath(); ctx.moveTo(-.12, -.56); ctx.lineTo(.12, -.56); ctx.lineTo(.2 + sw, -.1); ctx.quadraticCurveTo(0, -.06, -.2 + sw, -.1); ctx.closePath();
  ctx.fillStyle = (o.cols && o.cols[0] === '#b3202a') ? '#2a3f8f' : '#b3202a'; ctx.fill(); ctx.lineWidth = .014; ctx.strokeStyle = INK; ctx.stroke(); ctx.restore(); }
const PROPDRAW = {
  sword: (ctx, d) => { ctx.strokeStyle = '#d9dee6'; ctx.lineWidth = .02; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(d[0] * .34, d[1] * .34); ctx.stroke(); ctx.strokeStyle = '#8a5a2b'; ctx.lineWidth = .028; ctx.beginPath(); ctx.moveTo(-d[1] * .05, d[0] * .05); ctx.lineTo(d[1] * .05, -d[0] * .05); ctx.stroke(); },
  spear: (ctx, d) => { ctx.strokeStyle = '#8a5a2b'; ctx.lineWidth = .016; ctx.beginPath(); ctx.moveTo(-d[0] * .25, -d[1] * .25); ctx.lineTo(d[0] * .45, d[1] * .45); ctx.stroke(); ctx.fillStyle = '#c8cdd4'; ctx.beginPath(); ctx.arc(d[0] * .47, d[1] * .47, .03, 0, 7); ctx.fill(); },
  staff: (ctx, d) => { ctx.strokeStyle = '#7a4a2a'; ctx.lineWidth = .02; ctx.beginPath(); ctx.moveTo(0, .25); ctx.lineTo(0, -.3); ctx.stroke(); ctx.fillStyle = '#7ab8ff'; ctx.shadowColor = '#7ab8ff'; ctx.shadowBlur = 20; ctx.beginPath(); ctx.arc(0, -.33, .04, 0, 7); ctx.fill(); ctx.shadowBlur = 0; },
  bow: (ctx, d) => { ctx.strokeStyle = '#7a4a2a'; ctx.lineWidth = .016; ctx.beginPath(); ctx.arc(0, 0, .15, -1.2, 1.2); ctx.stroke(); ctx.strokeStyle = '#eee'; ctx.lineWidth = .005; ctx.beginPath(); ctx.moveTo(Math.cos(-1.2) * .15, Math.sin(-1.2) * .15); ctx.lineTo(Math.cos(1.2) * .15, Math.sin(1.2) * .15); ctx.stroke(); },
  lantern: (ctx, d) => { ctx.strokeStyle = INK; ctx.lineWidth = .008; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, .05); ctx.stroke(); ctx.fillStyle = '#ffd36b'; ctx.shadowColor = '#ffb030'; ctx.shadowBlur = 30; ctx.fillRect(-.03, .05, .06, .07); ctx.shadowBlur = 0; ctx.strokeRect(-.03, .05, .06, .07); },
  map: (ctx, d) => { ctx.fillStyle = '#e9d6a6'; ctx.strokeStyle = INK; ctx.lineWidth = .008; ctx.fillRect(-.02, -.06, .13, .1); ctx.strokeRect(-.02, -.06, .13, .1); ctx.strokeStyle = '#d8312b'; ctx.beginPath(); ctx.moveTo(.05, -.03); ctx.lineTo(.08, 0); ctx.moveTo(.08, -.03); ctx.lineTo(.05, 0); ctx.stroke(); },
  hammer: (ctx, d) => { ctx.strokeStyle = '#7a4a2a'; ctx.lineWidth = .016; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(d[0] * .2, d[1] * .2); ctx.stroke(); ctx.fillStyle = '#8a9099'; ctx.save(); ctx.translate(d[0] * .2, d[1] * .2); ctx.rotate(Math.atan2(d[1], d[0])); ctx.fillRect(-.02, -.05, .05, .1); ctx.restore(); },
  shield: (ctx, d) => { ctx.fillStyle = '#9aa3ad'; ctx.strokeStyle = INK; ctx.lineWidth = .01; ctx.beginPath(); ctx.arc(0, 0, .09, 0, 7); ctx.fill(); ctx.stroke(); ctx.fillStyle = '#d8312b'; ctx.beginPath(); ctx.arc(0, 0, .03, 0, 7); ctx.fill(); },
  book: (ctx, d) => { ctx.fillStyle = '#7a4bc4'; ctx.strokeStyle = INK; ctx.lineWidth = .008; ctx.fillRect(-.03, -.04, .08, .1); ctx.strokeRect(-.03, -.04, .08, .1); },
  phone: (ctx, d) => { ctx.fillStyle = '#26262e'; ctx.fillRect(-.02, -.05, .04, .08); ctx.fillStyle = '#6fc3ff'; ctx.fillRect(-.015, -.044, .03, .06); },
};
function propFor(name) { const fn = PROPDRAW[name]; if (!fn) return null;
  return (ctx, k, p, b, side) => { if (k !== 'R') return; ctx.save(); ctx.translate(p[0], p[1]); fn(ctx, [side * Math.sin(b), Math.cos(b)]); ctx.restore(); }; }
function stickA(ctx, o) {
  if (o.size && o.size !== 1 && !o._sized) o = Object.assign({}, o, { s: (o.s || 400) * o.size, _sized: true });
  if (o.propName && !o.prop && !o.sil) o = Object.assign({}, o, { prop: propFor(o.propName) });
  capeBehind(ctx, o); drawStick(ctx, o); accessory(ctx, o); extrasFront(ctx, o); }

// ---------- fable / story set pieces ----------
function castle(ctx, x, base, s, col, flagCol, t) { ctx.save(); ctx.translate(x, base); ctx.scale(s, s);
  const wall = '#b9b2a6', dark = '#8c857a';
  rrect(ctx, -160, -170, 320, 170, 4); fillStroke(ctx, wall, 5); for (let i = -160; i < 160; i += 40) { rrect(ctx, i, -195, 24, 28, 2); fillStroke(ctx, wall, 4); }
  for (const tx of [-170, 170]) { rrect(ctx, tx - 45, -300, 90, 300, 4); fillStroke(ctx, wall, 5); path(ctx, [[tx - 58, -300], [tx, -400], [tx + 58, -300]]); fillStroke(ctx, col, 5);
    line(ctx, tx, -400, tx, -460, 5); const w = Math.sin(t * 5 + tx) * 8; path(ctx, [[tx, -460], [tx + 60, -448 + w], [tx, -430]]); fillStroke(ctx, flagCol, 4);
    rrect(ctx, tx - 12, -230, 24, 40, 12); fillStroke(ctx, '#2a1f1f', 3); }
  ctx.beginPath(); ctx.moveTo(-40, 0); ctx.lineTo(-40, -70); ctx.arc(0, -70, 40, Math.PI, 0); ctx.lineTo(40, 0); fillStroke(ctx, '#3a2a20', 4);
  ctx.fillStyle = 'rgba(40,20,40,.18)'; ctx.fillRect(40, -300, 180, 300); ctx.restore(); }
function tinyArmy(ctx, x0, y0, cols, rows, col, t, dx = 0, seed = 1) { const R = rng(seed);
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { const x = x0 + c * 26 + (r % 2) * 13 + dx, y = y0 + r * 22 + Math.sin(t * 8 + c + r) * 2;
    line(ctx, x, y + 6, x, y + 22, 4, '#221c22'); circle(ctx, x, y, 9); fillStroke(ctx, col, 3); if (R() < .3) line(ctx, x + 6, y - 20, x + 6, y + 18, 3, '#6b5a4a'); } }
function interiorBG(ctx, cam, wall, floor) { applyCam(ctx, cam, .4); ctx.fillStyle = wall; ctx.fillRect(-600, -600, 2400, 2000);
  ctx.strokeStyle = mix(wall, '#000', .25); ctx.lineWidth = 4; for (let y = -600; y < 1400; y += 90) for (let x = -600 + (y / 90 % 2) * 70; x < 1800; x += 140) { ctx.strokeRect(x, y, 140, 90); }
  applyCam(ctx, cam, 1); rrect(ctx, -700, 1250, 2500, 1400, 0); fillStroke(ctx, floor, 6); }
function fireGlow(ctx, x, y, r, t, a = 1) { const k = .85 + .15 * Math.sin(t * 11) * Math.sin(t * 4.3); const g = ctx.createRadialGradient(x, y, 10, x, y, r * k);
  g.addColorStop(0, `rgba(255,190,90,${.75 * a})`); g.addColorStop(.4, `rgba(255,120,40,${.35 * a})`); g.addColorStop(1, 'rgba(255,90,20,0)'); ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2); }
function flames(ctx, x, y, s, t) { for (let i = 0; i < 5; i++) { const h = s * (.7 + .3 * Math.sin(t * 9 + i * 1.7)), w = s * .32; const px = x + (i - 2) * s * .22;
  path(ctx, [[px - w / 2, y], [px, y - h], [px + w / 2, y]]); fillStroke(ctx, i % 2 ? '#ffb43a' : '#ff6a2a', 3); } }
const SET2 = {
  kingdoms(ctx, lt, t, s) { const cam = { x: 540 + lt * 12, y: 980, z: 1.02 + lt * .03 }; const sv = Object.assign({}, s, { tod: s.tod == 'day' ? 'dusk' : s.tod });
    bg(ctx, t, cam, sv); applyCam(ctx, cam, .7); hills(ctx, 1160, '#3f6b3a', 11, 60);
    castle(ctx, 200, 1150, .9, '#c9302c', '#d8312b', t); castle(ctx, 880, 1150, .9, '#2f63c9', '#2f63c9', t);
    applyCam(ctx, cam, 1); tinyArmy(ctx, 40, 1330, 9, 4, '#d8312b', t, 0, 3); tinyArmy(ctx, 800, 1330, 9, 4, '#2f63c9', t, 0, 5); nightTint(ctx, sv); },
  armies(ctx, lt, t, s) { const cam = { x: 540, y: 960, z: 1 + lt * .05 }; applyCam(ctx, cam, 1); ctx.fillStyle = '#7aa64a'; ctx.fillRect(-600, -600, 2400, 3200);
    const R = rng(2); for (let i = 0; i < 120; i++) { circle(ctx, R() * 1300 - 100, R() * 2000, 3 + R() * 4); ctx.fillStyle = 'rgba(60,90,30,.35)'; ctx.fill(); }
    rrect(ctx, 520, -200, 40, 2400, 0); fillStroke(ctx, '#b48a55', 0); const adv = easeOut(clamp(lt / 2.2)) * 180;
    for (let r = 0; r < 14; r++) { tinyArmy(ctx, 60 + adv - r * 6, 300 + r * 90, 6, 1, '#d8312b', t, 0, r); tinyArmy(ctx, 860 - adv + r * 6, 300 + r * 90, 6, 1, '#2f63c9', t, 0, r + 30); }
    if (lt > 2) puff(ctx, 540, 1000, 160 * clamp(lt - 2), t, '#e9dcc0', 6, .8); },
  forge(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.03 + lt * .03 }; interiorBG(ctx, cam, '#4a3a3a', '#3a2c26');
    applyCam(ctx, cam, 1); rrect(ctx, 650, 900, 360, 380, 20); fillStroke(ctx, '#5a4a44', 6); rrect(ctx, 700, 1000, 260, 180, 90); fillStroke(ctx, '#1a1010', 5); flames(ctx, 830, 1170, 140, t);
    fireGlow(ctx, 830, 1100, 700, t); path(ctx, [[330, 1290], [520, 1290], [500, 1230], [560, 1200], [300, 1200], [350, 1230]]); fillStroke(ctx, '#4a4f58', 6);
    const swing = Math.sin(t * 6) > .6 ? -1.3 : 1.9; stickA(ctx, C(cast(s.who), { x: 330, y: 1460, s: 520, face: face(s.mood || 'calm', talkingAt(s, t), t), arms: { L: [.4, -.3], R: [swing, -.4] } }));
    if (Math.sin(t * 6) > .6) for (let i = 0; i < 8; i++) { const a = i / 8 * TAU; line(ctx, 440 + Math.cos(a) * 20, 1190 + Math.sin(a) * 20, 440 + Math.cos(a) * 60, 1190 + Math.sin(a) * 60, 4, '#ffd23a'); }
    darkness(ctx, .25, '#1a0a05'); },
  throne(ctx, lt, t, s) { const hh = handheld(t, 2), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.02 + lt * .025 }; interiorBG(ctx, cam, '#5a3e5e', '#7a2a2a');
    applyCam(ctx, cam, 1); for (const bx of [140, 940]) { rrect(ctx, bx - 70, 300, 140, 520, 6); fillStroke(ctx, '#b3262f', 5); star5(ctx, bx, 520, 40, 0, '#f2c230'); }
    path(ctx, [[400, 1300], [680, 1300], [800, 2400], [280, 2400]]); fillStroke(ctx, '#b3262f', 4); rrect(ctx, 420, 760, 240, 520, 30); fillStroke(ctx, '#d9a84a', 6); rrect(ctx, 450, 820, 180, 300, 20); fillStroke(ctx, '#8a2a3a', 5);
    fireGlow(ctx, 160, 300, 260, t, .6); fireGlow(ctx, 920, 300, 260, t, .6);
    stickA(ctx, C(cast(s.who), { x: 540, y: 1420, s: 520, face: face(s.mood || 'smug', talkingAt(s, t), t), acc: 'crown', arms: { L: [.3, -.1], R: [.9, -2.2] } })); },
  blueprint(ctx, lt, t, s) { const cam = { x: 540, y: 960, z: 1.05 - lt * .02, r: -.02 }; applyCam(ctx, cam, 1); ctx.fillStyle = '#1d4f9a'; ctx.fillRect(-600, -600, 2400, 3200);
    ctx.strokeStyle = 'rgba(255,255,255,.18)'; ctx.lineWidth = 2; for (let x = -600; x < 1800; x += 60) line(ctx, x, -600, x, 2600, 2, 'rgba(255,255,255,.15)'); for (let y = -600; y < 2600; y += 60) line(ctx, -600, y, 1800, y, 2, 'rgba(255,255,255,.15)');
    const k = clamp(lt / 1.2); ctx.save(); ctx.strokeStyle = '#eaf2ff'; ctx.lineWidth = 7; ctx.setLineDash([2400 * k, 2400]);
    ctx.beginPath(); ctx.moveTo(380, 700); ctx.quadraticCurveTo(380, 1150, 540, 1260); ctx.quadraticCurveTo(700, 1150, 700, 700); ctx.closePath(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(150, 980); ctx.lineTo(330, 980); ctx.moveTo(300, 955); ctx.lineTo(335, 980); ctx.lineTo(300, 1005); ctx.stroke(); ctx.restore();
    text(ctx, (s.label || 'THE PLAN').toUpperCase().slice(0, 18), 540, 520, 64, '#eaf2ff', null, 0, 'Lora', 700);
    const st = backOut(clamp((lt - .9) / .3)); if (st > 0) { ctx.save(); ctx.translate(540, 1160); ctx.rotate(-.12); ctx.scale(st, st); rrect(ctx, -230, -60, 460, 120, 10); fillStroke(ctx, 'rgba(0,0,0,0)', 10, '#e0392f');
      text(ctx, (s.hl || 'TOP SECRET').toUpperCase().slice(0, 12), 0, 0, 70, '#e0392f', null, 0, 'Poppins', 700); ctx.restore(); } },
  bridge(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.02 + lt * .03 }; bg(ctx, t, cam, Object.assign({}, s, { ground: 'grass' }));
    applyCam(ctx, cam, 1); ctx.fillStyle = '#3f8fc0'; ctx.fillRect(-600, 1350, 2400, 1200); for (let i = 0; i < 12; i++) line(ctx, (i * 170 + t * 90) % 1500 - 200, 1420 + (i % 4) * 60, (i * 170 + t * 90) % 1500 - 120, 1420 + (i % 4) * 60, 5, 'rgba(255,255,255,.4)');
    rrect(ctx, -100, 1250, 1280, 70, 6); fillStroke(ctx, '#b9b2a6', 6); for (const ax of [100, 540, 980]) { ctx.beginPath(); ctx.arc(ax, 1420, 130, Math.PI, 0); ctx.lineTo(ax + 150, 1320); ctx.lineTo(ax - 150, 1320); ctx.closePath(); fillStroke(ctx, '#9c958a', 6); }
    stickA(ctx, C(cast(s.who), { x: 380, y: 1255, s: 420, face: face(s.mood, talkingAt(s, t), t), arms: { L: [.3, -.1], R: [1.3, -.4] } }));
    stickA(ctx, C(cast(s.who + 1), { x: 720, y: 1255, s: 420, flip: -1, face: face('calm', false, t, 1.1) })); nightTint(ctx, s); },
  messenger(ctx, lt, t, s) { const cam = { x: 540 + lt * 50, y: 960, z: 1.05 }; bg(ctx, t * 2.4, cam, Object.assign({}, s, { ground: 'road' })); applyCam(ctx, cam, .5); castle(ctx, 1150, 1180, .5, '#2f63c9', '#2f63c9', t); applyCam(ctx, cam, 1);
    stickA(ctx, C(cast(s.who), { x: 380 + lt * 50, y: 1440, s: 500, legs: walkLegs(t, 15, .9), arms: { L: [.3 + Math.sin(t * 15) * .9, -.3], R: [1.6, -.2] }, lean: .15, face: face(s.mood || 'scared', false, t) }));
    const hx = 380 + lt * 50 + 150, hy = 1440 - 390; rrect(ctx, hx - 15, hy - 45, 30, 90, 10); fillStroke(ctx, '#f3e2b8', 5); puff(ctx, 280 + lt * 50, 1450, 46, t, '#e9dcc0', Math.floor(t * 8), .7); nightTint(ctx, s); },
};
Object.assign(SETUPS, SET2);


// ---------- adventure / pirate set pieces (for screenplay scripts) ----------
function rainFx(ctx, t, a = 1) { ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.strokeStyle = `rgba(200,215,255,${.45 * a})`; ctx.lineWidth = 3; ctx.beginPath();
  for (let i = 0; i < 170; i++) { const x = (rnd(i) * 1300 + t * 160) % 1300 - 100, y = (rnd(i + 7) * 2100 + t * 1700) % 2100 - 100; ctx.moveTo(x, y); ctx.lineTo(x - 16, y + 52); } ctx.stroke();
  if ((Math.floor(t * 3) % 5 == 0) && Math.sin(t * 40) > .3) { ctx.fillStyle = 'rgba(235,240,255,.55)'; ctx.fillRect(0, 0, W, H); } ctx.restore(); }
function rnd(i) { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function palm(ctx, x, base, s, col = '#1f4a2a') { ctx.save(); ctx.translate(x, base); ctx.scale(s, s); ctx.beginPath(); ctx.moveTo(-10, 0); ctx.quadraticCurveTo(10, -180, 30, -360); ctx.lineTo(48, -360); ctx.quadraticCurveTo(30, -180, 14, 0); fillStroke(ctx, '#5a3b22', 4);
  for (let k = 0; k < 6; k++) { const a = -Math.PI / 2 + (k - 2.5) * .55; ctx.beginPath(); ctx.moveTo(40, -360); ctx.quadraticCurveTo(40 + Math.cos(a) * 120, -360 + Math.sin(a) * 120 - 40, 40 + Math.cos(a) * 230, -330 + Math.sin(a) * 160); ctx.lineTo(40 + Math.cos(a) * 200, -320 + Math.sin(a) * 150); fillStroke(ctx, col, 4); } ctx.restore(); }
function eyesGlow(ctx, x, y, t, col = '#ffe14d') { const open = (t * 1.3 % 3) > .2; if (!open) return; for (const dx of [-22, 22]) { ellipse(ctx, x + dx, y, 12, 8); ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 20; ctx.fill(); ctx.shadowBlur = 0; } }
function skeleton(ctx, x, y, s, t, k) { const o = { x, y, s, sil: '#efe9dc', bob: Math.sin(t * 5 + k) * .01, arms: { L: [2.3 + Math.sin(t * 6 + k) * .3, .2], R: [.4, -.2] }, legs: { L: [.15, -.05], R: [.15, -.05] }, shadow: false };
  drawStick(ctx, o); const hy = y - .765 * s, r = .19 * s; for (const dx of [-.07, .07]) { circle(ctx, x + dx * s, hy, r * .3); ctx.fillStyle = '#221c22'; ctx.fill(); }
  path(ctx, [[x - r * .4, hy + r * .5], [x + r * .4, hy + r * .5], [x, hy + r * .25]]); ctx.fillStyle = '#221c22'; ctx.fill(); line(ctx, x + .1 * s, y - .6 * s, x + .25 * s, y - 1.1 * s, s * .015, '#8a7a60'); }
const SET3 = {
  storm(ctx, lt, t, s) { const sh = shake(t, 10, .8), cam = { x: 540 + sh[0], y: 960 + sh[1], z: 1.04, r: Math.sin(t * 1.3) * .05 }; applyCam(ctx, cam, .08); drawSky(ctx, '#151a2e', '#3b4462');
    applyCam(ctx, cam, .2); drawCloud(ctx, 200 + t * 30, 260, 160, 1, .6); drawCloud(ctx, 800 + t * 40, 200, 140, 2, .5); applyCam(ctx, cam, .45); drawSea(ctx, 900, t * 2.2, 2600, ['#2f5a7a', '#173a56', '#0c2438']);
    applyCam(ctx, cam, 1); ctx.save(); ctx.translate(540, 1080); ctx.rotate(Math.sin(t * 1.6) * .12); drawShip(ctx, 0, 0, 1.1, t, { flag: '#1b1820', hull: '#4a2e22' }); ctx.restore();
    stickA(ctx, C(cast(s.who), { x: 520, y: 950, s: 170, lean: Math.sin(t * 1.6) * .2, face: face(s.mood || 'scared', talkingAt(s, t), t) })); rainFx(ctx, t); darkness(ctx, .15, '#05081a'); },
  treasuremap(ctx, lt, t, s) { const cam = { x: 540, y: 960, z: 1.0 + lt * .08 }; applyCam(ctx, cam, .5); ctx.fillStyle = '#5a3a22'; ctx.fillRect(-600, -600, 2400, 3200);
    applyCam(ctx, cam, 1); const un = easeOut(clamp(lt / .7)); ctx.save(); ctx.translate(540, 980); ctx.scale(.3 + .7 * un, 1); rrect(ctx, -420, -560, 840, 1120, 30); fillStroke(ctx, '#e8d3a0', 8); ctx.restore();
    if (un > .9) { ctx.save(); ctx.strokeStyle = 'rgba(90,60,30,.7)'; ctx.lineWidth = 6; ctx.setLineDash([22, 18]); ctx.beginPath(); ctx.moveTo(260, 1360); ctx.quadraticCurveTo(420, 1100, 520, 1180); ctx.quadraticCurveTo(650, 1260, 700, 860); ctx.stroke(); ctx.restore();
      hills(ctx, 760, 'rgba(120,90,50,.35)', 4, 60); path(ctx, [[220, 640], [330, 520], [440, 640]]); fillStroke(ctx, 'rgba(110,80,40,.5)', 5);
      const g = .6 + .4 * Math.sin(t * 6); ctx.save(); ctx.shadowColor = '#ff3b30'; ctx.shadowBlur = 40 * g; line(ctx, 650, 810, 750, 910, 20, '#d8312b'); line(ctx, 750, 810, 650, 910, 20, '#d8312b'); ctx.restore(); }
    text(ctx, (s.label && s.label != 'X' ? s.label : 'TREASURE').toUpperCase().slice(0, 14), 540, 500, 70, '#5a3a22', null, 0, 'Lora', 700); },
  jungle(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0] + lt * 20, y: 960 + hh[1], z: 1.03 }; applyCam(ctx, cam, .1); drawSky(ctx, '#20304a', '#5a6a5a');
    applyCam(ctx, cam, .3); for (let i = 0; i < 6; i++) palm(ctx, i * 230 - 60, 1250, .9, '#1d3a2a'); applyCam(ctx, cam, 1); rrect(ctx, -700, 1300, 2500, 1400, 0); fillStroke(ctx, '#1f3a22', 6);
    eyesGlow(ctx, 860, 980, t); eyesGlow(ctx, 190, 1060, t + 1.3, '#ff5a3a');
    stickA(ctx, C(cast(s.who), { x: 420 + lt * 20, y: 1440, s: 500, legs: walkLegs(t, 7, .4), arms: walkArms(t, 7, .4), face: face(s.mood || 'scared', talkingAt(s, t), t) }));
    stickA(ctx, C(cast(s.who + 1), { x: 680 + lt * 20, y: 1460, s: 460, flip: -1, legs: walkLegs(t + .5, 7, .4), face: face('scared', false, t, 1) }));
    applyCam(ctx, cam, 1.4); for (let i = 0; i < 4; i++) palm(ctx, i * 420 - 150, 2050, 1.6, '#0c1f12'); darkness(ctx, .25, '#06120a'); },
  skeletons(ctx, lt, t, s) { const sh = shake(t, 5 * Math.max(0, 1 - lt), 2), cam = { x: 540 + sh[0], y: 960 + sh[1], z: 1.03 + lt * .03 };
    bg(ctx, t, cam, Object.assign({}, s, { tod: 'night' })); applyCam(ctx, cam, 1); darkness(ctx, .35, '#0a0c20'); applyCam(ctx, cam, 1);
    const rise = easeOut(clamp(lt / .8)); [[650, 1450, 420], [880, 1430, 380], [420, 1470, 360]].forEach(([x, y, z], k) => { ctx.save(); ctx.beginPath(); ctx.rect(-600, -600, 2400, y + 600 - 4); ctx.clip(); skeleton(ctx, x, y + (1 - rise) * z * 1.2, z, t, k); ctx.restore(); });
    stickA(ctx, C(cast(s.who), { x: 200, y: 1480, s: 480, face: face(s.mood || 'shocked', talkingAt(s, t), t), arms: { L: [.3, -.1], R: [1.4, -.5] } })); },
  temple(ctx, lt, t, s) { const cam = { x: 540, y: 960, z: 1.02 + lt * .04 }; applyCam(ctx, cam, .1); drawSky(ctx, '#2a2240', '#6a5070');
    applyCam(ctx, cam, 1); rrect(ctx, 140, 380, 800, 1000, 10); fillStroke(ctx, '#7a7468', 8); for (let y = 420; y < 1360; y += 110) line(ctx, 150, y, 930, y, 4, '#5f5a50');
    const open = easeOut(clamp((lt - .4) / 1.2)); ctx.save(); const gl = ctx.createRadialGradient(540, 980, 20, 540, 980, 420); gl.addColorStop(0, `rgba(120,180,255,${.8 * open})`); gl.addColorStop(1, 'rgba(120,180,255,0)'); ctx.fillStyle = gl; ctx.fillRect(140, 380, 800, 1000); ctx.restore();
    for (const side of [-1, 1]) { rrect(ctx, 540 + (side > 0 ? 0 : -250) + side * open * 200, 640, 250, 740, 6); fillStroke(ctx, '#5e594f', 6); }
    circle(ctx, 540, 520, 70); fillStroke(ctx, '#e9e2d0', 6); for (const dx of [-24, 24]) { circle(ctx, 540 + dx, 510, 16); ctx.fillStyle = '#221c22'; ctx.fill(); }
    rrect(ctx, -600, 1380, 2400, 1200, 0); fillStroke(ctx, '#4a4038', 6); if (lt < 1.6) puff(ctx, 540, 1380, 120 * open, t, '#cfc6b4', 3, .6);
    stickA(ctx, C(cast(s.who), { x: 300, y: 1500, s: 420, face: face(s.mood || 'shocked', talkingAt(s, t), t), arms: { L: [.3, -.1], R: [1.5, -.3] } })); },
  ghost(ctx, lt, t, s) { const cam = { x: 540 + Math.sin(t * .8) * 8, y: 960, z: 1.03 + lt * .03 }; applyCam(ctx, cam, .2); drawSky(ctx, '#071510', '#163828');
    applyCam(ctx, cam, 1); rrect(ctx, -600, 1380, 2400, 1200, 0); fillStroke(ctx, '#0f2218', 6); drawChest(ctx, 540, 1430, 1.1, .6);
    const g = cast.ghostIdx != null ? CAST[cast.ghostIdx] : null; const gy = 1180 - easeOut(clamp(lt / 1)) * 160 + Math.sin(t * 2) * 14;
    ctx.save(); ctx.globalAlpha = .62; ctx.shadowColor = '#5dff9a'; ctx.shadowBlur = 60; stickA(ctx, C(g || cast(1), { x: 540, y: gy, s: 620, sil: '#8dffc0', shadow: false, arms: { L: [2.2, .4], R: [1.2, -.3] } })); ctx.restore();
    if (s.speaker && /ghost/i.test(s.speaker)) eyesGlow(ctx, 540, gy - .765 * 620, t, '#ff3b30');
    for (let i = 0; i < 12; i++) puff(ctx, 300 + i * 50, 1400 - (t * 60 + i * 37) % 300, 40, t, '#2f8a55', i, .25);
    const hero = cast.ghostIdx != null && s.who == cast.ghostIdx ? 0 : s.who; stickA(ctx, C(cast(hero), { x: 200, y: 1500, s: 400, face: face(s.speaker && /ghost/i.test(s.speaker) ? 'scared' : (s.mood || 'shocked'), talkingAt(s, t) && !/ghost/i.test(s.speaker || ''), t), arms: POSE.handsUp.arms })); },
};
Object.assign(SETUPS, SET3);
cast.ghostIdx = CAST.findIndex(c => c.ghost);
if (cast.ghostIdx < 0) cast.ghostIdx = null;

const SHOTS = [];


// ---------- animation cues from the script's Animation/Visual lines (s.fx), drawn over the AI picture ----------
const FXH = (i, k) => { const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };   // fixed random, same every frame
function fxBefore(s, lt, t) {   // camera: zoom, pan, tilt, shake
  const f = s.fx || [], o = { z: 0, x: 0, y: 0, r: 0 };
  const sp = f.includes('slowmo') ? .45 : 1;
  if (f.includes('zoom')) o.z += .16 * ease(clamp(lt / Math.max(1, s.dur || 3)));
  if (f.includes('pan')) o.x += (lt * 40 * sp) % 400 - 60;
  if (f.includes('tilt')) o.r += Math.sin(t * 1.7 * sp) * .045, o.y += Math.sin(t * 1.7 * sp + 1) * 18;
  if (f.includes('shake') || f.includes('boom')) { const k = f.includes('boom') ? Math.max(0, 1 - lt / .8) : .5; o.x += Math.sin(t * 61) * 14 * k; o.y += Math.cos(t * 53) * 12 * k; }
  return o;
}
function fxAfter(ctx, s, lt, t) {
  const f = s.fx || []; if (!f.length) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (f.includes('fog')) for (let k = 0; k < 4; k++) {
    const x = ((t * (18 + k * 9) + k * 300) % 1600) - 260, y = 700 + k * 260, g = ctx.createRadialGradient(x, y, 0, x, y, 520);
    g.addColorStop(0, 'rgba(225,230,240,.30)'); g.addColorStop(1, 'rgba(225,230,240,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
  if (f.includes('smoke')) for (let k = 0; k < 7; k++) {
    const ph = (t * .25 + FXH(k, 1)) % 1, x = 300 + FXH(k, 2) * 500 + Math.sin(t + k) * 40, y = 1500 - ph * 900, r = 140 + ph * 260;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, `rgba(90,255,150,${.28 * (1 - ph)})`); g.addColorStop(1, 'rgba(90,255,150,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
  if (f.includes('fire')) { const fl = .55 + .25 * Math.sin(t * 13) + .2 * Math.sin(t * 29); const g = ctx.createLinearGradient(0, H, 0, H * .45);
    g.addColorStop(0, `rgba(255,120,20,${.45 * fl})`); g.addColorStop(1, 'rgba(255,80,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    for (let k = 0; k < 26; k++) { const ph = (t * (.5 + FXH(k, 3)) + FXH(k, 4)) % 1; ctx.fillStyle = `rgba(255,${150 + 90 * FXH(k, 5) | 0},40,${1 - ph})`;
      ctx.beginPath(); ctx.arc(FXH(k, 6) * W + Math.sin(t * 3 + k) * 20, H - ph * 900, 5 + 5 * (1 - ph), 0, 7); ctx.fill(); } }
  if (f.includes('eyes')) [[250, 760], [820, 690], [560, 980], [130, 1120]].forEach(([x, y], k) => {
    const bl = ((t + k * .7) % 2.6) < .12 ? .1 : 1; ctx.fillStyle = '#ffe23a'; ctx.shadowColor = '#ffe23a'; ctx.shadowBlur = 30;
    [-22, 22].forEach(dx => { ctx.beginPath(); ctx.ellipse(x + dx, y, 13, 9 * bl, 0, 0, 7); ctx.fill(); }); ctx.shadowBlur = 0; });
  if (f.includes('sparkle')) for (let k = 0; k < 14; k++) { const ph = (t * .35 + FXH(k, 7)) % 1, a = Math.sin(ph * Math.PI);
    sparkle(ctx, 120 + FXH(k, 8) * 840, 1500 - ph * 1000, 18 + 26 * FXH(k, 9), a); }
  if (f.includes('coins')) for (let k = 0; k < 18; k++) { const ph = (t * (.45 + .3 * FXH(k, 10)) + FXH(k, 11)) % 1, x = 80 + FXH(k, 12) * 920, y = -60 + ph * 2000;
    ctx.save(); ctx.translate(x, y); ctx.scale(Math.abs(Math.cos(t * 6 + k)) + .15, 1); ctx.fillStyle = '#ffcc2e'; ctx.strokeStyle = '#a8740c'; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.arc(0, 0, 26, 0, 7); ctx.fill(); ctx.stroke(); ctx.restore(); }
  if (f.includes('dust')) for (let k = 0; k < 30; k++) { const ph = (lt * .5 + FXH(k, 13)) % 1; ctx.fillStyle = `rgba(200,180,150,${.6 * (1 - ph)})`;
    ctx.beginPath(); ctx.arc(FXH(k, 14) * W, 200 + ph * 1500, 4 + 6 * FXH(k, 15), 0, 7); ctx.fill(); }
  if (f.includes('rain')) { ctx.strokeStyle = 'rgba(200,215,255,.55)'; ctx.lineWidth = 3; ctx.beginPath();
    for (let k = 0; k < 140; k++) { const x = (FXH(k, 16) * 1300 + t * 260) % 1300 - 110, y = (FXH(k, 17) * 2100 + t * 2300) % 2100 - 100; ctx.moveTo(x, y); ctx.lineTo(x - 18, y + 70); }
    ctx.stroke(); ctx.fillStyle = 'rgba(20,30,60,.18)'; ctx.fillRect(0, 0, W, H); }
  if (f.includes('lightning')) { const c = (t % 3.1); if (c < .22) { ctx.fillStyle = `rgba(235,240,255,${.75 * (1 - c / .22)})`; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 9; ctx.shadowColor = '#bcd0ff'; ctx.shadowBlur = 40; ctx.beginPath(); let x = 300 + FXH(Math.floor(t / 3.1), 18) * 500, y = 0; ctx.moveTo(x, y);
    for (let k = 1; k < 9; k++) { x += (FXH(k, Math.floor(t / 3.1)) - .5) * 160; y += 110; ctx.lineTo(x, y); } ctx.stroke(); ctx.shadowBlur = 0; } }
  if (f.includes('clash')) { const c = (lt * 1.6) % 1; if (c < .35) { const k = 1 - c / .35; burst(ctx, 545, 1340, 170 * (1.2 - k * .4), 10, '#fff4b0', 7);
    for (let j = 0; j < 10; j++) { const a = j / 10 * 6.28 + lt, r = 60 + 220 * (1 - k); ctx.fillStyle = '#ffd23a'; ctx.beginPath(); ctx.arc(545 + Math.cos(a) * r, 1340 + Math.sin(a) * r, 9 * k + 2, 0, 7); ctx.fill(); } } }
  if (f.includes('boom') && lt < .9) { const k = easeOut(clamp(lt / .5)); burst(ctx, 540, 1100, 520 * k, 14, '#ffae2a', 9); darkness(ctx, .55 * (1 - lt / .9), '#fff'); }
  if (f.includes('arrow')) { const k = clamp((lt % 1.4) / .5); if (k < 1) { const x = 80 + k * 900, y = 1250 - k * 260; ctx.strokeStyle = '#fff'; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.moveTo(x - 160, y + 46); ctx.lineTo(x, y); ctx.stroke(); ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(x, y, 12, 0, 7); ctx.fill(); } }
  if (f.includes('bubble')) { const k = backOut(clamp(lt / .45)); ctx.save(); ctx.translate(700, 820); ctx.scale(k, k);
    ctx.fillStyle = '#fff'; ctx.strokeStyle = INK; ctx.lineWidth = 9; ctx.beginPath(); ctx.ellipse(0, 0, 270, 190, 0, 0, 7); ctx.fill(); ctx.stroke();
    [[-150, 250, 34], [-210, 330, 20]].forEach(([x, y, r]) => { ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); ctx.stroke(); });
    for (let j = 0; j < 7; j++) { ctx.fillStyle = '#ffcc2e'; ctx.strokeStyle = '#a8740c'; ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(-120 + (j % 4) * 80 + (j > 3 ? 40 : 0), (j > 3 ? 40 : -30) + Math.sin(t * 4 + j) * 8, 32, 0, 7); ctx.fill(); ctx.stroke(); }
    ctx.restore(); }
  ctx.restore();
}

// ---------- 'ai' mode: AI-illustrated background per scene, stick characters acting on top (reference-video style) ----------
SETUPS.aibg = function (ctx, lt, t, s) {
  const img = window.BG && window.BG[s.bg]; const i = D.segs.indexOf(s); const dir = i % 2 ? 1 : -1;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#111'; ctx.fillRect(0, 0, W, H);
  const hh = handheld(t, 2.5), fo = fxBefore(s, lt, t), z = 1.04 + lt * .022 + fo.z, px = dir * (8 + lt * 9) + fo.x;
  if (img && img.naturalWidth) { ctx.save(); ctx.translate(540 + px + hh[0], 960 + hh[1] + fo.y); ctx.rotate(fo.r); ctx.scale(z + Math.abs(fo.r) * 2, z + Math.abs(fo.r) * 2); ctx.drawImage(img, -540, -960, 1080, 1920); ctx.restore(); }
  else { (SETUPS[s.base] || SETUPS.talk)(ctx, lt, t, s); return; }
  // ground shadow band so the characters sit in the picture
  const g = ctx.createLinearGradient(0, H * .72, 0, H); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.35)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  const cam = { x: 540 + px * .3, y: 960, z: 1 + lt * .012 }; applyCam(ctx, cam, 1);
  const tk = talkingAt(s, t), ghostSpeaks = /ghost/i.test(s.speaker || ''), fx = s.fx || [];
  let base = s.base || 'talk'; if (fx.includes('run') && !['closeup', 'impact'].includes(base)) base = 'run'; else if (fx.includes('walk') && !['closeup', 'impact'].includes(base)) base = 'walk';
  const jump = fx.includes('jump') ? -Math.abs(Math.sin(t * 5.2)) * 120 : 0; ctx.translate(0, jump);
  const gesture = tk ? { L: [.3, -.1], R: [1.2 + Math.sin(t * 5) * .2, -.6] } : POSE.idle.arms;
  if (ghostSpeaks && cast.ghostIdx != null) {
    const gy = 1500 + Math.sin(t * 2) * 14; ctx.save(); ctx.globalAlpha = .62; ctx.shadowColor = CAST[cast.ghostIdx].glow || '#5dff9a'; ctx.shadowBlur = 60;
    stickA(ctx, C(CAST[cast.ghostIdx], { x: 650, y: gy, s: 640, sil: CAST[cast.ghostIdx].glow || '#8dffc0', shadow: false, arms: { L: [2.2, .4], R: [1.2, -.3] } })); ctx.restore();
    stickA(ctx, C(cast(0), { x: 260, y: 1760, s: 470, face: face('scared', false, t), arms: POSE.handsUp.arms }));
  } else if (['talk', 'bridge', 'jungle'].includes(base) && CAST.length > 1) {
    const a = s.who || 0, b = (a + 1) % CAST.length;
    stickA(ctx, C(cast(a), { x: 330, y: 1760, s: 560, bob: Math.sin(t * 4) * .006, face: face(s.mood, tk, t), arms: gesture }));
    stickA(ctx, C(cast(b), { x: 770, y: 1780, s: 520, flip: -1, bob: Math.sin(t * 4 + 1) * .006, face: face('calm', false, t, 1.3) }));
  } else if (['crowd', 'armies', 'kingdoms'].includes(base)) {
    [[180, 1740, 380], [900, 1740, 380], [380, 1790, 440], [700, 1800, 440]].forEach(([x, y, z2], k) =>
      stickA(ctx, C(cast(k), { x, y, s: z2, flip: x > 540 ? -1 : 1, bob: Math.sin(t * 4 + k) * .01, face: face(s.mood, k == 0 && tk, t, k), arms: s.mood == 'happy' ? POSE.handsUp.arms : POSE.idle.arms })));
  } else if (base == 'closeup') {
    stickA(ctx, C(cast(s.who), { x: 540, y: 2250, s: 1300, shadow: false, headTilt: Math.sin(t * 1.6) * .03, face: face(s.mood, tk, t), arms: { L: [.25, -.1], R: [.25, -.1] } }));
  } else if (base == 'walk' || base == 'run' || base == 'messenger') {
    const sp = base == 'walk' ? 8 : 15;
    stickA(ctx, C(cast(s.who), { x: 300 + lt * 70, y: 1780, s: 560, legs: walkLegs(t, sp, base == 'walk' ? .5 : .9), arms: walkArms(t, sp, .8), lean: base == 'walk' ? .05 : .16, face: face(s.mood, tk, t) }));
  } else {
    stickA(ctx, C(cast(s.who), { x: i % 3 == 0 ? 540 : (i % 3 == 1 ? 340 : 740), y: 1770, s: 580, flip: i % 3 == 2 ? -1 : 1, bob: Math.sin(t * 3) * .006, face: face(s.mood, tk, t), arms: gesture }));
  }
  // the script's animation cues, then the reference videos' overlays on top of the picture
  ctx.setTransform(1, 0, 0, 1, 0, 0); fxAfter(ctx, s, lt, t);
  if (base == 'impact') { const k = easeOut(clamp(lt / .3)); burst(ctx, 640, 1000, 300 * k, 12, '#ffd23a', 5); if (s.label) text(ctx, s.label.toUpperCase().slice(0, 10), 640, 1000, 110 * k, '#fff', INK, 16); if (lt < .1) darkness(ctx, .4 * (1 - lt / .1), '#fff'); }
  if (base == 'reveal' || base == 'treasuremap') { const sa = kf(lt, [[.3, 0], [.5, 1], [1.2, .2]]); sparkle(ctx, 620, 1100, 90 * sa, sa); sparkle(ctx, 820, 1020, 60 * sa, sa); }
  if (base == 'bigtext' && (s.label || s.hl)) { const k = backOut(clamp(lt / .35)), word = (s.label || s.hl).toUpperCase().slice(0, 12); ctx.font = '700 200px Poppins'; const fs = Math.min(200, 200 * 860 / Math.max(1, ctx.measureText(word).width)); ctx.save(); ctx.translate(540, 900); ctx.rotate(-.04); ctx.scale(k, k); text(ctx, word, 0, 0, fs, '#ffd23a', INK, Math.max(10, fs * .09)); ctx.restore(); }
  if ((s.tod || 'day') == 'night') darkness(ctx, .12, '#0a0c30');
};

const SINGLE = ['bigtext', 'reveal', 'blueprint', 'treasuremap', 'temple'];   // keep in sync with pipeline/stick.py
D.segs.forEach((s, i) => { const start = i == 0 ? 0 : s.start, end = i + 1 < D.segs.length ? D.segs[i + 1].start : D.total;
  if (s.bg) { s.base = s.setup; } const fn = s.bg ? SETUPS.aibg : (SETUPS[s.setup] || SETUPS.talk); s.who = s.who || 0; const tr = (i % 3 == 2) ? 'cut' : 'whip';
  if (end - start > 4.2 && !SINGLE.includes(s.setup)) {   // the skill keeps shots 2-4 s: second angle for long lines
    const mid = start + (end - start) * .55, alt = s.bg ? ((ctx, lt, t, x) => SETUPS.aibg(ctx, lt, t, Object.assign({}, x, { base: x.base == 'closeup' ? 'talk' : 'closeup' }))) : (s.setup == 'closeup' ? SETUPS.talk : SETUPS.closeup);
    SHOTS.push({ start, end: mid, tr: 'cut', draw(ctx, lt, t) { fn(ctx, lt, t, s); } });
    SHOTS.push({ start: mid, end, tr, draw(ctx, lt, t) { alt(ctx, lt, t, s); } });
  } else SHOTS.push({ start, end, tr, draw(ctx, lt, t) { fn(ctx, lt, t, s); } }); });
