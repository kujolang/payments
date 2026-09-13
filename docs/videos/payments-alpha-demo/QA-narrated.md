# Narrated video verification — 2026-09-13

- User explicitly classified usage as noncommercial and requested attribution in the post only. No on-screen attribution was added.
- Provider confirmed Brian is a premade American English voice. One ElevenLabs request generated 343 characters with eleven_multilingual_v2 on the Free plan. Original MP3, request hash and character alignment retained. No credentials are stored in project artifacts.
- Five scenes were retimed from provider alignment, with 0.25-second audio lead-in and speech ending at 20.173 seconds inside a 21-second film. The closing card deliberately holds about five seconds to explain upcoming Link sandbox validation without rushing the speech.
- HyperFrames check passed runtime, layout and contrast. The existing advisory about five scenes sharing one track remains accepted; no findings suppressed.
- Final MP4 is H.264/yuv420p, 1080×1080, 30 fps, with a 48 kHz AAC track, both streams 21 seconds. Complete decoding succeeded.
- Final rendered audio was independently transcribed with local whisper.cpp tiny.en. All script words matched after punctuation/case normalization and the recognizer's Koojo → Kujo spelling normalization. No missing sentence or cut-off ending was detected. This is an automated intelligibility check, not a subjective listening review.
- Measured final audio: -13.69 LUFS integrated, -1.05 dBTP true peak, 3.40 LU loudness range. No measured clipping. No soundtrack to compete with speech.
- Six final-video frames visually reviewed, including the closing frame: readable fixture panels, persistent synthetic/no-money labels, proper order and no ElevenLabs branding on screen.
- Transcript and optional SRT derive from the exact generated text and provider timing. SRT is supplied separately, not burned into the video.
- Original silent MP4 remains unchanged. Live Link validation and deployment acceptance remain pending; the video does not establish financial readiness.
