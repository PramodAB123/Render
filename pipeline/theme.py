"""Pick the look and sound of a video from its own script (no genre box).
Scores the script's words against each theme profile in config.json "genres" and returns the best one.
Works for English and Hindi scripts. Nothing to read (daily runs) -> a different theme each day."""
import re
from collections import Counter

WORDS = {
    "horror": "ghost ghosts haunted scream screams blood dead death die dying corpse grave graves cursed curse demon "
              "monster monsters skeleton skeletons skull creepy dark darkness shadow shadows evil spirit spirits night fear "
              "terrified whisper whispers nightmare zombie witch भूत डर चीख खून मौत मरना कब्र श्राप शैतान राक्षस कंकाल अंधेरा "
              "आत्मा डरावना चुड़ैल",
    "comedy": "funny laugh laughs laughing joke jokes silly prank lol oops awkward hilarious stupid idiot dumb clumsy "
              "mom dad boss office pizza हंसी मजाक मज़ाक बेवकूफ पागल मस्ती",
    "science": "science scientist atom atoms planet planets space galaxy universe star stars energy physics chemistry "
               "experiment lab laboratory gravity light speed brain cell cells dna earth moon sun orbit neutron "
               "विज्ञान ग्रह अंतरिक्ष ब्रह्मांड तारे ऊर्जा प्रयोग",
    "motivation": "dream dreams goal goals discipline success succeed never give up hard work grind champion believe "
                  "yourself win winner fail failure strong stronger rise sapna सपना मेहनत सफलता हिम्मत जीत",
    "mystery": "mystery mysterious secret secrets clue clues vanished disappeared unknown unexplained strange detective "
               "missing signal case puzzle hidden truth रहस्य राज़ गायब सुराग अजीब",
    "history": "king kings queen kingdom empire emperor army armies war battle ancient century castle medieval roman "
               "pharaoh sword knight throne historians soldiers राजा रानी राज्य सम्राट सेना युद्ध प्राचीन किला तलवार",
    "adventure": "pirate pirates ship captain treasure island map jungle sea ocean storm journey quest adventure explore "
                 "explorer temple trap chest gold coins sail crew हीरो खज़ाना खजाना जहाज़ जहाज कैप्टन द्वीप समुद्र तूफान "
                 "जंगल मंदिर सोना सफर",
}
# phrases that count extra
STRONG = {"horror": ["ghost", "भूत", "haunted", "scream"], "adventure": ["treasure", "pirate", "खज़ाना", "जहाज़"],
          "comedy": ["joke", "funny"], "history": ["empire", "kingdom"], "mystery": ["vanished", "mystery"]}


def detect(text, profiles):
    """Best theme name for this text among the available profiles, or None if nothing matches."""
    if not text or not text.strip():
        return None
    toks = Counter(re.findall(r"[\wऀ-ॿ]+", text.lower()))
    score = {}
    for name, ws in WORDS.items():
        if name not in profiles:
            continue
        s = sum(toks[w] for w in set(ws.split()))
        s += sum(2 * toks[w] for w in STRONG.get(name, []))
        score[name] = s
    if not score or max(score.values()) == 0:
        return None
    best = max(score, key=score.get)
    print("  theme from script: " + ", ".join(f"{k} {v}" for k, v in sorted(score.items(), key=lambda x: -x[1]) if v), flush=True)
    return best
