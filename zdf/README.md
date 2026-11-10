# zdf mode: the zach-d-films skill, built from the script

Engine: `vendor/animation-skills/skills/zach-d-films/engine` (claude-animation-skills, MIT): procedural cartoon people
(`makeHuman`, outfits vest / chainmail / plate / knight / archer, plus casual clothes in the script's colours),
props (`pistol`, `bullet`, `sword`, `shield`, `mace`, `arrow`, `bow`, `stand`), sparks, the red force ripple, blue studio
sky, depth of field, bloom and the 1-3 word lower-third captions.

What is ours: `zdf/auto_shots.js` replaces the skill's hand-written example edit (`src/shots.js`). Nothing is preset:
`pipeline/zdf.py` turns every Visual step of the script into a shot:

- **People** from the step's words (one per person named: "a man in a steel vest ... a soldier holding a pistol"), the
  outfit from the words next to each person, poses from the action (walk, run, point, talk, think, scared, happy, sit,
  aim, swing, hit, fall).
- **Props**: the skill's own when named; anything else is a part recipe designed for this script
  (`pipeline/makers.py`, free local LLM) or built from the cinema library (jar, screen with the quoted words, document,
  sign, machine ...).
- **Impacts**: a weapon word + a hit word ("shoots", "swings ... hits") makes a slow-motion impact on the person in
  armour: the projectile crawls in, sparks, the red ripple spreads, the camera shakes.
- **Camera** from the step or the scene's Camera line (wide, medium, close-up, extreme close-up, low angle, orbit,
  tracking, aerial, zoom in/out, over the shoulder, dutch); long lines cut to a second angle.
- **Captions** with the skill's rule (1-3 words, broken at punctuation), and one dip to black on the "But" line.

A topic instead of a script (one short line in the script box) is written into a full screenplay in the skill's
format first (`pipeline/screenwriter.py`: hook, misconception, "But" twist, examples, mechanism, payoff), sized to the
chosen length.

Speed: on CPU-only machines the 3D renders at 3/4 resolution without MSAA (captions stay sharp), about 0.4 s a frame.
Set `ZDF_FULL=1` for the skill's full quality.
