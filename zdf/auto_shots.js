// zach-d-films skill, driven by the script: replaces the skill's hand-written example edit (src/shots.js).
// globalThis.ZDF (plan.js, written by pipeline/zdf.py) lists every shot: who is in it, what they wear and do,
// the props (the skill's own, or recipes designed for this script), any impact, and the camera.
// Uses the skill's building blocks: makeHuman / setPose / setMouth, props.js, anim.js, makeStage (sky, light, DoF, bloom).
import * as THREE from 'three';
import { makeHuman, standArmor } from './human.js';
import { pistol, gunArm, bullet, sword, shield, mace, arrow, bow, stand, glowSprite, sparks, streak, rippleOverlay } from './props.js';
import { kf, lerp, smooth, easeOut, easeIn, easeInOut, range, clamp, V, cam, place, shake } from './anim.js';

const Z = globalThis.ZDF || { duration: 5, captions: [], fades: [], shots: [] };
export const DURATION = Z.duration;
export const CAPTIONS = Z.captions;
export const FADES = Z.fades;

// ---------------- people ----------------
const STAND = { lSh: [0.05, 0, 0.16], rSh: [0.05, 0, -0.16], lEl: [-0.25, 0, 0], rEl: [-0.25, 0, 0], lHip: [0, 0, 0.07], rHip: [0, 0, -0.07], lAn: [0, 0, -0.07], rAn: [0, 0, 0.07] };
function pose(name, t, k = 0) {
  const s = Math.sin, b = s(t * 1.6 + k) * 0.012, p = { ...STAND, chest: [b, 0, 0] };
  const walk = (sp, a) => { const w = s(t * sp + k); Object.assign(p, { lHip: [w * a, 0, .07], rHip: [-w * a, 0, -.07], lKn: [Math.max(0, -w) * a * 1.4, 0, 0], rKn: [Math.max(0, w) * a * 1.4, 0, 0],
    lSh: [-w * a * .9, 0, .16], rSh: [w * a * .9, 0, -.16], lEl: [-.5, 0, 0], rEl: [-.5, 0, 0], drop: -Math.abs(s(t * sp + k)) * .02 }); };
  switch (name) {
    case 'walk': walk(6, .45); break;
    case 'run': case 'chase': walk(11, .9); p.chest = [.25, 0, 0]; break;
    case 'point': p.rSh = [-1.45, 0, -.15]; p.rEl = [-.1, 0, 0]; p.head = [0, -.2, 0]; break;
    case 'talk': p.rSh = [-.5 - .2 * s(t * 3 + k), 0, -.35]; p.rEl = [-1.2, 0, 0]; p.head = [.05 * s(t * 2.3 + k), .1 * s(t * 1.1 + k), 0]; break;
    case 'scared': p.lSh = [-.4, 0, 2.3]; p.rSh = [-.4, 0, -2.3]; p.lEl = [-1.6, 0, 0]; p.rEl = [-1.6, 0, 0]; p.chest = [-.15, 0, 0]; p.head = [-.2, 0, 0]; p.pelvis = [0, 0, s(t * 40) * .01]; break;
    case 'happy': case 'dance': p.lSh = [0, 0, 2.6 + .2 * s(t * 8)]; p.rSh = [0, 0, -2.6 - .2 * s(t * 8)]; p.drop = -Math.abs(s(t * 6)) * .05; break;
    case 'think': case 'look': p.rSh = [-1.9, 0, -.6]; p.rEl = [-2.3, 0, 0]; p.head = [.15, .25 * s(t * .8 + k), 0]; break;
    case 'hips': p.lSh = [.2, 0, .55]; p.rSh = [.2, 0, -.55]; p.lEl = [-1.9, -.4, 0]; p.rEl = [-1.9, .4, 0]; break;
    case 'sit': p.lHip = [-1.5, 0, .08]; p.rHip = [-1.5, 0, -.08]; p.lKn = [1.5, 0, 0]; p.rKn = [1.5, 0, 0]; p.drop = -.42; break;
    case 'sleep': p.lHip = [-1.5, 0, .1]; p.rHip = [-1.5, 0, -.1]; p.lKn = [1.6, 0, 0]; p.rKn = [1.6, 0, 0]; p.drop = -.42; p.head = [.5, 0, .3]; break;
    case 'aim': p.rSh = [-1.5, .1, -.05]; p.rEl = [0, 0, 0]; p.lSh = [-1.4, -.4, .1]; p.lEl = [-.3, 0, 0]; break;
    case 'swing': { const a = kf(t % 1.6, [[0, -2.6], [.5, -2.6], [.75, .6], [1.6, .6]], easeIn); p.rSh = [a, 0, -.3]; p.rEl = [-.3, 0, 0]; p.chest = [.15, -.4 * (a + 1) / 3, 0]; break; }
    case 'hit': { const a = clamp(Math.sin(Math.min(1, t * 2) * Math.PI)); p.chest = [-.35 * a, 0, .1 * a]; p.head = [-.3 * a, 0, 0]; p.lSh = [0, 0, .9 * a]; p.rSh = [0, 0, -.9 * a]; break; }
    case 'fall': { const a = easeIn(range(t, 0, 1.2)); p.chest = [-.6 * a, 0, 0]; p.drop = -.5 * a; break; }
  }
  return p;
}
const OUTFITS = new Set(['vest', 'chainmail', 'plate', 'knight', 'archer']);
function person(a) {
  const h = makeHuman(OUTFITS.has(a.outfit) ? a.outfit : 'casual');
  // casual clothes in the script's colours (materials are shared, so clone per person)
  const shirt = new THREE.Color(a.shirt || '#3a6ad8'), pants = new THREE.Color(a.pants || '#2a2e3a');
  h.root.updateMatrixWorld(true);
  if (!OUTFITS.has(a.outfit)) h.root.traverse(m => { if (m.isMesh && m.material && m.material.color && m.material.roughness > .88 && !m.material.map) {
    m.material = m.material.clone(); const up = m.getWorldPosition(new THREE.Vector3()).y > .9; m.material.color.copy(up ? shirt : pants); } });
  if (a.old) h.root.scale.set(.95, .92, .95);
  if (a.size) h.root.scale.multiplyScalar(a.size);
  if (a.ghost) h.root.traverse(m => { if (m.isMesh) { m.material = m.material.clone(); m.material.transparent = true; m.material.opacity = .45; m.material.emissive = new THREE.Color(a.glow || '#8dffc0'); m.material.emissiveIntensity = .6; } });
  return h;
}

// ---------------- props: the skill's own, or a recipe designed for this script ----------------
function textTex(lines, o = {}) {
  const c = document.createElement('canvas'); c.width = o.w || 512; c.height = o.h || 256; const x = c.getContext('2d');
  x.fillStyle = o.bg || '#0b1a2c'; x.fillRect(0, 0, c.width, c.height); const L = lines.filter(Boolean); let fs = o.fs || (L.length > 2 ? 40 : 64);
  x.textAlign = 'center'; x.textBaseline = 'middle';
  L.forEach((ln, i) => { let f = fs; x.font = `700 ${f}px Cap, sans-serif`; while (x.measureText(ln).width > c.width * .9 && f > 14) { f -= 3; x.font = `700 ${f}px Cap, sans-serif`; }
    x.fillStyle = (o.hl === i) ? '#e8262a' : (o.fg || '#6ad8ff'); x.fillText(ln, c.width / 2, c.height / 2 + (i - (L.length - 1) / 2) * fs * 1.2); });
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function fromRecipe(rc) {
  const g = new THREE.Group(); let top = 0, wide = .2;
  (rc.parts || []).forEach(p => { const z = p.size || [.3]; let geo;
    if (p.shape === 'box') geo = new THREE.BoxGeometry(z[0] || .3, z[1] || z[0] || .3, z[2] || z[0] || .3);
    else if (p.shape === 'sphere') geo = new THREE.SphereGeometry(z[0] || .2, 32, 20);
    else if (p.shape === 'cylinder') geo = new THREE.CylinderGeometry(z[0] || .1, z[1] || z[0] || .1, z[2] || .4, 32);
    else if (p.shape === 'cone') geo = new THREE.ConeGeometry(z[0] || .2, z[1] || .4, 28);
    else if (p.shape === 'torus') geo = new THREE.TorusGeometry(z[0] || .3, z[1] || .05, 16, 40);
    else if (p.shape === 'capsule') geo = new THREE.CapsuleGeometry(z[0] || .1, z[1] || .3, 6, 16);
    else if (p.shape === 'plane' || p.shape === 'text') geo = new THREE.PlaneGeometry(z[0] || .6, z[1] || .3);
    else return;
    const m = p.shape === 'text'
      ? new THREE.MeshBasicMaterial({ map: textTex(String(p.text || '').split('\n'), { fg: p.color || '#6ad8ff', bg: p.bg || '#0b1a2c', hl: p.hl, w: 512, h: Math.round(512 * (z[1] || .3) / (z[0] || .6)) }), side: THREE.DoubleSide, toneMapped: false })
      : new THREE.MeshPhysicalMaterial({ color: p.color || '#9aa3ad', roughness: p.metal ? .3 : .55, metalness: p.metal ? 1 : 0, clearcoat: .2, transparent: (p.opacity ?? 1) < 1, opacity: p.opacity ?? 1,
          transmission: (p.opacity ?? 1) < .5 ? .6 : 0, emissive: p.glow ? (p.color || '#ffffff') : '#000000', emissiveIntensity: p.glow || 0, side: p.shape === 'plane' ? THREE.DoubleSide : THREE.FrontSide });
    const me = new THREE.Mesh(geo, m); me.position.set(...(p.pos || [0, 0, 0])); me.rotation.set(...(p.rot || [0, 0, 0])); me.castShadow = me.receiveShadow = p.shape !== 'text'; g.add(me);
    const bb = new THREE.Box3().setFromObject(me); top = Math.max(top, bb.max.y); wide = Math.max(wide, bb.max.x - bb.min.x, bb.max.z - bb.min.z);
    if ((p.glow || 0) > .8) { const l = new THREE.PointLight(p.color || '#ffffff', p.glow * .8, 2); l.position.copy(me.position); g.add(l); } });
  g.userData = { size: rc.size || Math.max(top, wide, .2), focusY: rc.focusY ?? top * .55, motion: rc.motion || 'none' };
  return g;
}
const LIB = { pistol, sword, shield, mace, arrow, bow, stand, bullet: () => bullet(1) };
function makeProp(p) {
  if (LIB[p.kind]) { const o = LIB[p.kind](); const bb = new THREE.Box3().setFromObject(o); o.userData.size = Math.max(.2, bb.getSize(new THREE.Vector3()).length()); o.userData.focusY = (bb.max.y + bb.min.y) / 2; return o; }
  return fromRecipe(p.recipe || { parts: [] });
}
function animateProp(o, t) {
  const mo = o.userData.motion; if (!mo || mo === 'none') return;
  if (mo === 'spin' || mo === 'orbit') o.rotation.y = t * 1.4;
  if (mo === 'bob' || mo === 'float') o.position.y = (o.userData.y0 ??= o.position.y) + Math.sin(t * 2) * (mo === 'float' ? .12 : .04);
  if (mo === 'pulse') o.scale.setScalar(1 + Math.sin(t * 5) * .05);
  if (mo === 'swing') o.rotation.z = Math.sin(t * 2) * .25;
  if (mo === 'rock') o.rotation.x = Math.sin(t * 1.6) * .08;
  if (mo === 'flicker') o.traverse(m => { if (m.material && m.material.emissiveIntensity != null) m.material.emissiveIntensity = (m.material.userData.e0 ??= m.material.emissiveIntensity) * (.6 + .4 * Math.abs(Math.sin(t * 17))); });
}

// ---------------- camera angles (aimed at what the shot is about) ----------------
function aim(kind, c, s, x, h) {
  switch (kind) {
    case 'establishing': return [[c.x + s * (1.6 - x * .6), c.y + s * (1.6 - x * .5), c.z + s * (3.6 - x)], [c.x, c.y + s * .45, c.z]];
    case 'wide': return [[c.x - s * (.9 - x * .5), c.y + s * .75, c.z + s * 2.9], [c.x, c.y + s * .5, c.z]];
    case 'low_hero': return [[c.x + s * (.7 - x * .3), c.y + s * .12, c.z + s * 1.7], [c.x, c.y + s * .65, c.z]];
    case 'closeup': return [[h.x + s * .12, h.y + s * .02, h.z + s * (1.15 - .12 * x)], [h.x, h.y, h.z]];
    case 'ecu': return [[h.x + s * .05, h.y, h.z + s * (.4 - .08 * x)], [h.x, h.y, h.z]];
    case 'orbit': { const a = .8 - x * 1.0; return [[c.x + Math.sin(a) * s * 2.2, c.y + s * .8, c.z + Math.cos(a) * s * 2.2], [c.x, c.y + s * .5, c.z]]; }
    case 'dolly_in': return [[c.x + s * .3, c.y + s * .6, c.z + s * (2.6 - 1.5 * easeInOut(x))], [c.x, c.y + s * .55, c.z]];
    case 'pull_back': return [[c.x + s * .3, c.y + s * (.6 + .6 * x), c.z + s * (1.0 + 2.4 * easeInOut(x))], [c.x, c.y + s * .5, c.z]];
    case 'aerial': return [[c.x + s * .4, c.y + s * 4, c.z + s * 1.2], [c.x, c.y, c.z]];
    case 'tracking': case 'side': return [[c.x, c.y + s * .55, c.z + s * 2.4], [c.x, c.y + s * .5, c.z]];
    case 'over_shoulder': return [[c.x - s * 1.1, c.y + s * .85, c.z + s * 1.0], [c.x + s * .4, c.y + s * .6, c.z]];
    case 'two_shot': return [[c.x + s * .2 * x, c.y + s * .7, c.z + s * 2.6], [c.x, c.y + s * .55, c.z]];
    case 'dutch': return [[c.x + s * 1.3, c.y + s * .4, c.z + s * 1.4], [c.x, c.y + s * .6, c.z]];
    default: return [[c.x + s * .5, c.y + s * .7, c.z + s * 2.2], [c.x, c.y + s * .55, c.z]];
  }
}

// ---------------- one shot from the plan ----------------
function buildShot(D, { makeStage }) {
  const scene = makeStage({ shadowSize: 3.5 });
  const people = (D.actors || []).map((a, i, A) => { const h = person(a); const n = A.length;
    h.root.position.set(a.x ?? (i - (n - 1) / 2) * 1.05, 0, a.z ?? -(i % 2) * .25); h.root.rotation.y = a.face ?? (n > 1 ? (i < n / 2 ? .45 : -.45) : -.3); scene.add(h.root); h.home = h.root.position.clone(); return h; });
  const props = (D.props || []).map((p, i) => { const o = makeProp(p);
    if (p.hold != null && people[p.hold]) { const h = people[p.hold], wr = p.kind === 'bow' ? h.j.lWr : (p.kind === 'shield' ? h.j.lWr : h.j.rWr); wr.add(o);
      o.position.set(0, -.06, p.kind === 'shield' ? .08 : 0); if (p.kind === 'sword' || p.kind === 'mace') o.rotation.set(Math.PI, 0, 0); o.userData.held = true; return o; } const slots = [[.0, 0, .55], [.9, 0, .3], [-.95, 0, .3], [1.6, 0, -.4], [-1.6, 0, -.4]];
    const [x, y, z] = p.at || slots[(people.length ? i + 1 : i) % slots.length]; o.position.set(x, y + (p.lift || 0), z); scene.add(o); return o; });
  const looseProps = props.filter(o => !o.userData.held);
  // an impact: a projectile or a swing reaching a target (slow motion, sparks, the red force ripple)
  let imp = null;
  if (D.impact) {
    const I = D.impact, tgtH = people[I.target ?? (people.length > 1 ? 1 : 0)];
    const hitP = tgtH ? V(tgtH.root.position.x, 1.32 * (tgtH.root.scale.y || 1), tgtH.root.position.z + .12) : (props[0] ? props[0].position.clone().add(V(0, props[0].userData.focusY || .4, 0)) : V(0, 1.2, 0));
    const from = hitP.clone().add(V(-2.2, .05, 1.2)); const dir = hitP.clone().sub(from).normalize();
    const proj = I.weapon === 'arrow' ? arrow() : I.weapon === 'bullet' ? bullet(1) : null;
    if (proj) { scene.add(proj); if (proj.morphTargetInfluences) proj.scale.setScalar(1.4); }
    const sp = sparks(140, { speed: .9, spread: 1.4, gravity: -1.2, life: 1.0, size: .006, dir: dir.clone().negate(), seed: 5, color: [1, .5, .15] }); sp.position.copy(hitP); scene.add(sp);
    const disc = new THREE.Mesh(new THREE.CircleGeometry(.45, 48), new THREE.MeshBasicMaterial({ visible: false })); disc.position.copy(hitP).add(dir.clone().multiplyScalar(-.02)); disc.lookAt(from); scene.add(disc);
    const rip = rippleOverlay(disc); rip.material.visible = true;
    const fl = glowSprite(0xffb070, .02); fl.position.copy(hitP); scene.add(fl);
    const tr = streak(); scene.add(tr);
    let shooter = people.find((p, i) => i !== (I.target ?? (people.length > 1 ? 1 : 0)));
    if (shooter && tgtH) { shooter.root.position.set(tgtH.root.position.x - 2.0, 0, tgtH.root.position.z + .9); shooter.root.lookAt(tgtH.root.position.x, 0, tgtH.root.position.z); shooter.home = shooter.root.position.clone(); tgtH.root.rotation.y = -.9; }
    if (shooter && I.weapon === 'bullet') { const pg = pistol(); shooter.j.rWr.add(pg); pg.position.set(0, -.06, .04); pg.rotation.set(0, -Math.PI / 2, -Math.PI / 2); }
    if (shooter && I.weapon === 'arrow') { const bw = bow(); shooter.j.lWr.add(bw); bw.position.set(0, -.05, 0); }
    if (shooter && I.weapon === 'sword') { const sw = sword(); shooter.j.rWr.add(sw); sw.position.set(0, -.05, 0); sw.rotation.set(Math.PI, 0, 0); }
    let gun = null; if (I.weapon === 'bullet' && !shooter && people.length < 2) { gun = gunArm(); gun.position.copy(from); gun.rotation.y = -Math.atan2(dir.z, dir.x); gun.rotation.z = Math.asin(dir.y); scene.add(gun); }
    imp = { I, hitP, from, dir, proj, sp, rip, fl, tr, tgtH, shooter, TI: Math.min(1.4, (D.dur || 3) * .45) };
  }
  const c = cam(D.shot === 'closeup' || D.shot === 'ecu' ? 30 : 36);
  return { scene, camera: c, update(t) {
    const dur = D.dur || 3, x = clamp(t / dur);
    people.forEach((h, i) => { let a = (D.acts || [])[i] || 'idle';
      if (imp && h === imp.tgtH) a = t > imp.TI ? 'hit' : 'idle'; if (imp && h === imp.shooter) a = imp.I.weapon === 'bullet' ? 'aim' : imp.I.weapon === 'arrow' ? 'aim' : 'swing';
      h.setPose(pose(a === 'idle' ? (D.speaker === i ? 'talk' : 'idle') : a, a === 'hit' ? t - imp.TI : t, i));
      const talking = D.speaker === i && (D.words || []).some(w => D.start + t >= w.s && D.start + t <= w.e); h.setMouth(talking ? .35 + .35 * Math.abs(Math.sin(t * 18)) : (a === 'scared' || a === 'hit' ? .8 : 0));
      if (a === 'walk' || a === 'run' || a === 'chase') { const sp = a === 'walk' ? .6 : 1.6; h.root.rotation.y = Math.PI / 2 * (i % 2 ? -1 : 1); h.root.position.x = h.home.x + (i % 2 ? -1 : 1) * sp * (t - dur / 2); } });
    props.forEach(o => animateProp(o, t));
    let bloom = .35, s = 1.6, cc = V(0, 0, 0), hh = V(0, 1.55, 0);
    if (imp) {   // slow motion: the projectile crawls in, hits at TI, sparks + ripple spread
      const { proj, hitP, from, dir, sp, rip, fl, tr, TI } = imp; const it = t - TI;
      const pos = it < 0 ? hitP.clone().addScaledVector(dir, -(TI - t) * .35 - .02) : hitP.clone().addScaledVector(dir, -.02);
      if (proj) { proj.position.copy(pos); proj.quaternion.setFromUnitVectors(V(0, 1, 0), dir); if (proj.morphTargetInfluences) proj.morphTargetInfluences[0] = easeOut(range(it, 0, .4)); }
      if (proj) tr.set(pos.clone().addScaledVector(dir, -.25), pos, .002, it < 0 ? .5 : 0); else tr.set(pos, pos, .001, 0);
      sp.update(it); rip.material.uniforms.uCenter.value.set(0, 0, 0); rip.material.uniforms.uRadius.value = it > 0 ? Math.min(.45, it * .5) : 0; rip.material.uniforms.uAmp.value = it > 0 ? Math.max(0, 1 - it * .5) : 0; rip.material.uniforms.uTime.value = t;
      fl.scale.setScalar(it > 0 ? .05 + it * .2 : .001); fl.material.opacity = it > 0 ? Math.max(0, .8 - it) : 0;
      cc = it < 0 && proj ? pos.clone().setY(0) : hitP.clone().setY(0); hh = it < 0 && proj ? pos : hitP; s = it < 0 && proj ? .55 : .9; bloom = it > 0 ? .9 : .5;
    } else if (D.focusObj != null && props[D.focusObj] && !props[D.focusObj].userData.held) { const o = props[D.focusObj]; cc = o.position.clone(); s = Math.max(.45, o.userData.size * 1.4); hh = o.position.clone().add(V(0, o.userData.focusY || .4, 0)); cc.y = hh.y - s * .55; }
    else if (people.length) { people.forEach(h => cc.add(h.root.position)); cc.multiplyScalar(1 / people.length); cc.y = 0; s = 1.4 + (people.length - 1) * .45;
      const f = people[D.focus ?? 0] || people[0]; f.j.head.getWorldPosition(hh); if (D.shot === 'closeup' || D.shot === 'ecu') s = 1.4; }
    else if (looseProps.length) { cc = looseProps[0].position.clone(); s = Math.max(.6, looseProps[0].userData.size * 1.4); hh = cc.clone().add(V(0, looseProps[0].userData.focusY || .4, 0)); }
    let shot = D.shot || 'wide'; if (D.split && t > dur * .55) shot = D.shot2 || 'closeup';
    const xx = D.split ? (t > dur * .55 ? range(t, dur * .55, dur) : range(t, 0, dur * .55)) : x;
    const [p, l] = imp ? (t < imp.TI ? [[hh.x - .9, hh.y + .12, hh.z + 1.3], [hh.x + .2, hh.y, hh.z]] : [[hh.x + .9 - .2 * range(t, imp.TI, dur), hh.y + .15, hh.z + 2.1], [hh.x, hh.y - .1, hh.z]]) : aim(shot, cc, s, xx, hh);
    const k = shake(t, imp && t > imp.TI ? 2.5 : .8); place(c, [p[0] + k[0], Math.max(.08, p[1] + k[1]), p[2] + k[2]], l, shot === 'dutch' ? .12 : 0);
    const focus = c.position.distanceTo(new THREE.Vector3(...l));
    return { dof: { focus, aperture: shot === 'closeup' || shot === 'ecu' || imp ? .02 : .004, maxblur: .01 }, bloom, exposure: D.dark ? .55 : 1.0 };
  } };
}

export const SHOTS = Z.shots.map(D => ({ start: D.start, end: D.end, build: (env) => buildShot(D, env) }));
