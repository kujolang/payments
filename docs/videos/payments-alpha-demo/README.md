# Kujo Payments developer alpha demo

Attach `kujo-payments-alpha-demo.mp4` to a social post. 20 seconds, square 1080p, 30 fps, intentionally silent. Uses the Kujo ten-style skill's **Short Real-Product Launch** direction.

This is a synthetic fixture demonstration, not a completed Stripe Link payment. The visible terminal panels reproduce selected real fields from the fixture request and captured output; long identifiers are omitted. Approval is simulated. Link adapter sandbox validation remains pending. No partnership, production-readiness, or physical-isolation claim is made.

## Reproduce

With Node.js, Chromium and FFmpeg available:

```sh
npm run check -- --snapshots
npm run render -- --quality high --fps 30 --output kujo-payments-alpha-demo.mp4
```

CLI is pinned in package.json. Composition uses local GSAP and Departure Mono assets. No account, voice service, real credentials, or payment provider is needed to render. The financial fixture is separate; render never executes it.

BRIEF.md and STORYBOARD.md record editorial intent; sources.json and evidence/ preserve provenance; QA.md and render-metadata.json record verification. index.html is editable source. No video has been published by this workflow.
