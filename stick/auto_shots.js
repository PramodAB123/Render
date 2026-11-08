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
    drawStick(ctx, C(cast(s.who), { x: 540, y: 2050, s: 1500, bob: Math.sin(t * 3) * .004, headTilt: Math.sin(t * 1.6) * .03, shadow: false, face: face(s.mood, talkingAt(s, t), t), arms: { L: [.25, -.1], R: [.25, -.1] } }));
    if (s.mood == 'scared' || s.mood == 'shocked') sweat(ctx, 760, 900, 60, clamp(lt * 3)); nightTint(ctx, s); },
  talk(ctx, lt, t, s) { const hh = handheld(t, 4), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.02 + lt * .02 };
    bg(ctx, t, cam, s); applyCam(ctx, cam, 1); const a = cast(s.who), b = cast(s.who + 1), tk = talkingAt(s, t);
    drawStick(ctx, C(a, { x: 330, y: 1420, s: 520, bob: Math.sin(t * 4) * .006, face: face(s.mood, tk, t), arms: tk ? { L: [.3, -.1], R: [1.2 + Math.sin(t * 5) * .2, -.6] } : POSE.idle.arms }));
    drawStick(ctx, C(b, { x: 780, y: 1440, s: 470, flip: -1, bob: Math.sin(t * 4 + 1) * .006, face: face(s.other_mood || 'calm', false, t, 1.3), arms: POSE.idle.arms })); nightTint(ctx, s); },
  walk(ctx, lt, t, s) { const cam = { x: 540 + lt * 30, y: 960, z: 1.04 }; const sv = Object.assign({}, s); bg(ctx, t * 1.6, cam, sv); applyCam(ctx, cam, 1);
    for (let i = 0; i < 4; i++) drawBarrel(ctx, ((i * 520 - lt * 260) % 2080 + 2080) % 2080 - 300, 1400, .9);
    drawStick(ctx, C(cast(s.who), { x: 420 + lt * 30, y: 1430, s: 520, legs: walkLegs(t), arms: walkArms(t), lean: .06, bob: Math.abs(Math.sin(t * 9)) * .01, face: face(s.mood, talkingAt(s, t), t) })); nightTint(ctx, s); },
  run(ctx, lt, t, s) { const cam = { x: 540 + lt * 60, y: 960 + Math.sin(t * 18) * 6, z: 1.05 }; bg(ctx, t * 3, cam, s); applyCam(ctx, cam, 1);
    drawStick(ctx, C(cast(s.who), { x: 400 + lt * 60, y: 1430, s: 520, legs: walkLegs(t, 16, .9), arms: walkArms(t, 16, 1.1), lean: .18, bob: Math.abs(Math.sin(t * 16)) * .02, face: face(s.mood || 'scared', false, t) }));
    puff(ctx, 300 + lt * 60, 1440, 50, t, '#f3efe6', Math.floor(t * 8), .7); if (s.mood == 'scared') sweat(ctx, 520 + lt * 60, 900, 40, .9); nightTint(ctx, s); },
  crowd(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1 + lt * .03 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    const up = s.mood == 'happy' || s.mood == 'scared' || s.mood == 'shocked';
    [[150, 1380, 330], [930, 1380, 330], [330, 1430, 400], [760, 1440, 400], [540, 1480, 470]].forEach(([x, y, sz], k) =>
      drawStick(ctx, C(cast(k), { x, y, s: sz, flip: x > 540 ? -1 : 1, bob: Math.sin(t * 4 + k) * .01, face: face(s.mood, k == 4 && talkingAt(s, t), t, k), arms: up ? { L: [2.5 + Math.sin(t * 6 + k) * .2, .3], R: [2.5 - Math.sin(t * 6 + k) * .2, .3] } : POSE.idle.arms }))); nightTint(ctx, s); },
  object(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.02 + lt * .03 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    const pop = backOut(clamp(lt / .35)); ctx.save(); ctx.translate(720, 1420); ctx.scale(pop, pop); drawCrate(ctx, 0, 0, 420, 330, 0, (s.label || '???').toUpperCase().slice(0, 14)); ctx.restore();
    drawStick(ctx, C(cast(s.who), { x: 270, y: 1440, s: 500, face: face(s.mood || 'smug', talkingAt(s, t), t), arms: { L: [.3, -.1], R: [1.55, -.15] } })); nightTint(ctx, s); },
  reveal(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 1000 + hh[1], z: 1.05 + lt * .04 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    const open = easeOut(clamp((lt - .3) / .5)); drawChest(ctx, 680, 1460, 1.5, open);
    drawStick(ctx, C(cast(s.who), { x: 300, y: 1460, s: 500, face: face(open > .5 ? 'happy' : 'shocked', talkingAt(s, t), t), arms: open > .5 ? POSE.handsUp.arms : POSE.idle.arms }));
    const sa = kf(lt, [[.6, 0], [.8, 1], [1.4, .2]]); sparkle(ctx, 640, 1150, 90 * sa, sa); sparkle(ctx, 800, 1110, 60 * sa, sa);
    if (s.label) text(ctx, s.label.toUpperCase().slice(0, 16), 680, 1000 - 40 * open, 90 * open, '#ffe14d', INK, 14); },
  night(ctx, lt, t, s) { const cam = { x: 540 + Math.sin(t * .7) * 10, y: 960, z: 1.04 + lt * .03 }; bg(ctx, t, cam, Object.assign({}, s, { tod: 'night' })); applyCam(ctx, cam, 1);
    darkness(ctx, .45); applyCam(ctx, cam, 1); drawLantern(ctx, 760, 1180, 1.6, .8 + Math.sin(t * 9) * .1, t);
    const g = ctx.createRadialGradient(760, 1150, 20, 760, 1150, 700); g.addColorStop(0, 'rgba(255,200,110,.35)'); g.addColorStop(1, 'rgba(255,200,110,0)'); ctx.fillStyle = g; ctx.fillRect(-500, 0, 2500, 2400);
    drawStick(ctx, C(cast(s.who), { x: 380, y: 1450, s: 520, face: face(s.mood || 'scared', talkingAt(s, t), t), arms: { L: [.6, -.9], R: [.6, -.9] }, lean: -.05 + Math.sin(t * 30) * .01 }));
    sweat(ctx, 520, 860, 46, .9); },
  impact(ctx, lt, t, s) { const sh = shake(t, 26 * Math.max(0, 1 - lt * 2), 3), cam = { x: 540 + sh[0], y: 960 + sh[1], z: 1.08 - lt * .03 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    const k = easeOut(clamp(lt / .3)); burst(ctx, 650, 930, 330 * k, 12, '#ffd23a', 5); if (s.label) text(ctx, s.label.toUpperCase().slice(0, 10), 650, 930, 120 * k, '#fff', INK, 16);
    puff(ctx, 540, 1460, 140 * k, t, '#f3efe6', 4, 1 - clamp(lt - .6));
    drawStick(ctx, C(cast(s.who), { x: 330, y: 1460, s: 500, lean: -.25 * k, face: face('dizzy', false, t), arms: POSE.handsUp.arms }));
    if (lt < .12) darkness(ctx, .5 * (1 - lt / .12), '#fff'); nightTint(ctx, s); },
  sea(ctx, lt, t, s) { const hh = handheld(t, 4), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1 + lt * .03 }; bg(ctx, t, cam, Object.assign({}, s, { ground: 'sea' })); applyCam(ctx, cam, 1);
    drawStick(ctx, C(cast(s.who), { x: 760, y: 935, s: 130, face: face(s.mood, false, t) })); nightTint(ctx, s); },
  bigtext(ctx, lt, t, s) { const cam = { x: 540, y: 960, z: 1 + lt * .03 }; applyCam(ctx, cam, .2); drawSky(ctx, D.style.accent, mix(D.style.accent, '#000', .35));
    applyCam(ctx, cam, 1); const k = backOut(clamp(lt / .35)); const word = (s.label || s.hl || '').toUpperCase().slice(0, 12);
    ctx.font = `700 240px Poppins`; const fs = Math.min(240, 240 * 860 / Math.max(1, ctx.measureText(word).width));   // fit inside the safe area
    ctx.save(); ctx.translate(540, 900); ctx.rotate(-.04); ctx.scale(k, k); text(ctx, word, 0, 0, fs, '#fff', INK, Math.max(10, fs * .09)); ctx.restore();
    drawStick(ctx, C(cast(s.who), { x: 540, y: 1600, s: 420, face: face(s.mood || 'shocked', talkingAt(s, t), t), arms: POSE.handsUp.arms })); },
  think(ctx, lt, t, s) { const hh = handheld(t, 3), cam = { x: 540 + hh[0], y: 960 + hh[1], z: 1.03 + lt * .03 }; bg(ctx, t, cam, s); applyCam(ctx, cam, 1);
    drawStick(ctx, C(cast(s.who), { x: 440, y: 1450, s: 560, headTilt: .08, face: face('think', talkingAt(s, t), t), arms: { L: [.3, -.1], R: [.4, -2.6] } }));
    for (let i = 0; i < 3; i++) { const a = clamp((lt - i * .25) * 3); if (a > 0) text(ctx, '?', 660 + i * 90, 760 - i * 70 - Math.sin(t * 3 + i) * 10, 110 * a, '#fff', INK, 12); } nightTint(ctx, s); },
};
const SHOTS = [];
D.segs.forEach((s, i) => { const start = i == 0 ? 0 : s.start, end = i + 1 < D.segs.length ? D.segs[i + 1].start : D.total;
  const fn = SETUPS[s.setup] || SETUPS.talk; s.who = s.who || 0;
  SHOTS.push({ start, end, tr: (i % 3 == 2) ? 'cut' : 'whip', draw(ctx, lt, t) { fn(ctx, lt, t, s); } }); });
