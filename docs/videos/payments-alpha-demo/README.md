# Kujo Payments developer alpha demo

**Narrated version:** `kujo-payments-alpha-narrated.mp4` — 21 seconds, square 1080p, 30 fps, ElevenLabs Brian American English voiceover.

**Original silent version:** `kujo-payments-alpha-demo.mp4` — 20 seconds, retained unchanged.

[Transcript](narration/TRANSCRIPT.md) · [Optional SRT subtitles](narration/transcript.srt) · [Narration provenance and attribution](narration/RIGHTS.md).

The user explicitly classified this use as noncommercial. Include `elevenlabs.io` or `11.ai` in the publication title under the provider's Free-plan terms. Attribution belongs in the post; there is none on screen. This take is not commercially licensed. Nothing has been posted by this workflow.

Uses the Kujo ten-style skill's Short Real-Product Launch direction. The terminal excerpts are from a synthetic fixture, not a completed Link transaction. Approval and confirmation are simulated; Link sandbox validation remains pending. No partnership, production-readiness, or physical-isolation demonstration is claimed.

## Reproduce the narrated version

```sh
npm run check -- --snapshots
npm run render -- --quality high --fps 30 --output kujo-payments-alpha-narrated.mp4
```

Node.js, Chromium and FFmpeg are needed. The CLI is pinned; media assets and the completed narration are local. Rendering does not regenerate speech or execute payments. index.html is editable source. BRIEF.md, STORYBOARD.md, cue-map.json and narration/generation-receipt.json preserve the timing and provenance. QA-narrated.md records current verification; QA.md and render-metadata.json apply to the original silent export.
