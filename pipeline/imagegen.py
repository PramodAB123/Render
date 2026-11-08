"""Free AI scene images, generated on the runner's own CPU (no API, no key, no account).

Model: Lykon/dreamshaper-8-lcm (Stable Diffusion 1.5 fine-tune, license CreativeML OpenRAIL-M:
commercial use of the images is allowed; the license forbids harmful/illegal uses).
LCM = only ~6 denoising steps, so one 768x448 image takes roughly 10-25 s on a GitHub runner CPU.
"""
import os
from common import load_config

_pipe = None


def _load():
    global _pipe
    if _pipe is None:
        import torch
        from diffusers import AutoPipelineForText2Image, LCMScheduler
        c = load_config()["image"]
        torch.set_num_threads(os.cpu_count() or 4)
        print(f"  loading image model {c['model']} (first run downloads ~2 GB, then it is cached)")
        _pipe = AutoPipelineForText2Image.from_pretrained(c["model"], torch_dtype=torch.float32,
                                                          safety_checker=None, requires_safety_checker=False)
        _pipe.scheduler = LCMScheduler.from_config(_pipe.scheduler.config)
        _pipe.set_progress_bar_config(disable=True)
    return _pipe


def generate(prompt, out, portrait, style, seed=0):
    """Writes a PNG to `out`. Raises on failure (caller falls back to stock footage)."""
    import torch
    c = load_config()["image"]; w, h = c["size"]
    if portrait:
        w, h = h, w
    full = f"{prompt}, {style}, highly detailed, realistic, cinematic composition"
    img = _load()(full, negative_prompt=c["negative"], num_inference_steps=c["steps"], guidance_scale=c["guidance"],
                  width=w, height=h, generator=torch.Generator().manual_seed(seed)).images[0]
    img.save(out)
    return out
