# Tableside: 68 s hackathon demo video

- `tableside_demo.mp4`: full narration (1920×1080, H.264/AAC, 68 s). Committed so judges can watch it on GitHub.
- `tableside_demo_live_narration.mp4`: identical, except the final MuJoCo segment has music only, so
  a presenter can narrate it live. Git-ignored (local presenter copy).

**Footage is real project evidence only:**
- Codex's Isaac café PPO cup-holder run (colored K1).
- Codex's sensor-only, hand-carried pizza-and-drink MuJoCo delivery, shown in real time by
  cross-fading recorded frames at their timestamps.
- SmolVLA and GR00T N1.7 fine-tuning curves from the logged training runs, with a QR code to the
  Weights & Biases project.
- Every on-screen claim is captioned with its evidence kind (simulation, 1 trial).

**Narration:** OpenAI `gpt-4o-mini-tts`, voice "sage". Music is a synthesized pad (no licensed
tracks).

**Rebuild:** `sim/.venv/bin/python build_demo_video.py`. It needs the narration WAVs, which are
regenerated with `tts.py` and an API key from the ignored `.env`. Keys are never committed.
