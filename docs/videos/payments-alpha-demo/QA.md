# Render verification — 2026-09-13

- Actual synthetic fixture completed with exit 0. Captured output contains awaiting_authorization followed by succeeded. No Link API or real funds used.
- Verified visible request fields against the fixture source and output fields against evidence/output.txt. Long execution/receipt IDs are explicitly omitted from visual excerpts.
- Native HyperFrames 0.8.36 check passed runtime, layout and contrast. 19 seek positions cover first/last frame, scene midpoints and seams ±1 frame; 51 contrast checks passed. No runtime or layout findings.
- One advisory accepted: five scenes share one track. For this 20-second composition they are explicitly labeled, contiguous and independently editable. No check suppressions added. Dedicated motion assertions were not enabled.
- Reviewed browser snapshots and six frames decoded from the final MP4 in contact-sheet.jpg: no clipped text, correct scene order, large headline and terminal text, persistent synthetic/no-money label, held closing CTA. First frame is readable.
- FFprobe confirms H.264, yuv420p, 1080×1080, 30 fps, 20 seconds, one video stream and no audio stream. Full FFmpeg decode completed without errors.
- Silence is intentional. No listening review applies. No paid media or external publication occurred.
- The demo does not demonstrate a human approval session, physical credential isolation, a live Link transaction, or production financial readiness. Link sandbox and deployment acceptance remain outside this video task.
- Vendored font and GSAP are local. HyperFrames compiler may resolve/cache its default fonts during preparation; this workflow did not require a HeyGen account.
