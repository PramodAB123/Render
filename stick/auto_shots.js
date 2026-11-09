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
  else if (a === 'cap') { ctx.beginPath(); ctx.arc(0, -r * .5, r * .98, Math.PI * 1.05, Math.PI * 1.95); ctx.closePath(); fillStroke(ctx, o.capCol || '#2f6b3f', lw); rrect(ctx, r * .1, -r * .62, r * 1.25, r * .16, r * .08); fillStroke(ctx, o.capCol || '#2f6b3f', lw); }
  ctx.restore(); }
function stickA(ctx, o) { drawStick(ctx, o); accessory(ctx, o); }

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

const SHOTS = [];
D.segs.forEach((s, i) => { const start = i == 0 ? 0 : s.start, end = i + 1 < D.segs.length ? D.segs[i + 1].start : D.total;
  const fn = SETUPS[s.setup] || SETUPS.talk; s.who = s.who || 0;
  SHOTS.push({ start, end, tr: (i % 3 == 2) ? 'cut' : 'whip', draw(ctx, lt, t) { fn(ctx, lt, t, s); } }); });
