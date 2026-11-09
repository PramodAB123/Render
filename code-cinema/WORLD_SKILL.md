---
name: code-cinema-world
description: Turn any script into a 3D video where every animal, person, creature, vehicle and place the script names is built in code (three.js), acted out with simple rigs and filmed with a library of camera angles. No preset scene - the script decides what exists.
---

# Code Cinema World: the script builds the scene

`engine/world.html` is a toolkit, not a template. `pipeline/world.py` reads the script and decides which tools to use;
the engine assembles the models, the place, the motion and the camera for every line. Everything is a pure function of
time `t`, so frames are captured one by one (same `engine/render.js` as code-cinema, with `CINEMA_PAGE=world.html`).

## 1. Model builders (actors)

| Builder | Makes | Parts it rigs |
|---|---|---|
| `quadruped(preset)` | lion, lioness, tiger, leopard, cheetah, cat, dog, wolf, fox, horse, zebra, giraffe, elephant, rhino, hippo, bear, polar bear, cow, bull, pig, sheep, goat, deer, camel, rabbit, mouse, dragon, dinosaur, crocodile, monkey | body, 4 legs, neck, head, jaw, ears, mane, tail chain, trunk, tusks, horns/antlers, wings, spikes, stripes/spots textures |
| `biped(design)` | people (colours, hat, beard, cape, prop from the script's character description), robots, ghosts | legs, arms, head, jaw, hat, cape, held prop |
| `bird(preset)` | bird, eagle, owl, parrot, crow, bat, penguin, duck, chicken | wings, head, legs |
| `fish(preset)` | fish, shark, whale, dolphin | tail, fins |
| `vehicle()` | car, truck | wheels |

A new animal is one line in `Q` (body length/height/thickness, colours, head size, extras).

## 2. Place builders (environments)

`ENV`: savanna, jungle, forest, desert, snow, beach, ocean, underwater, city, village, farm, mountain, cave, space, moon,
room, castle, graveyard, ship. Each is a ground colour, a sky gradient, fog and a list of procedural props
(acacia, palm, pine, cactus, rock, bush, grass, dune, ice, crystal, coral, building, house, barn, fence, castle, grave,
planet, stars ...). Time of day (`day / dawn / dusk / night`) relights the place; weather adds rain, snow, fog, lightning.

## 3. Motions (actions)

`act()`: idle (breathing, tail sway), walk, run, chase, roar (jaw open, mane swell, camera shake), jump, fly, swim,
sleep, eat, sit, attack (lunge), look, scared, happy/dance, drive, talk (jaw/head follow the voice's word timings).

## 4. Camera angles

`SHOT`: establishing, wide, low_hero, closeup, orbit, tracking, aerial, dolly_in, pull_back, two_shot, over_shoulder,
dutch. Every angle is aimed at the actors in the shot (their position, size and head), so it works for a mouse or an
elephant. Lines longer than 4.2 s cut to a second angle halfway.

## How the script picks the tools (`pipeline/world.py`)

- **Who**: named characters from the screenplay (an animal word in the name makes them that animal; otherwise a person
  designed from their description) plus every creature the script mentions. Each line shows the ones it names or who
  speak; "he/she/it" keeps the last subject in shot.
- **Where**: the first place word in the scene's Visual line; a scene that names none stays put; with no place at all,
  the main animal's habitat (lion -> savanna, penguin -> snow, shark -> underwater).
- **What**: the first action word in the line (roar, run, fly, sleep ...).
- **Camera**: line 1 establishing; roars and shouts close-up; movement tracked; two characters talking two-shot;
  otherwise the angle library in turn.
- Captions: bold uppercase words in the top third, the spoken word highlighted, from the voice's word timings.
