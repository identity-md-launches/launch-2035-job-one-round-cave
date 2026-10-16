# The Shared Load — mark 30

Two bundles share one branch and one carrying limit. The carrying branch and
its two small woven sacks accompany ZipBatch: consider the whole load before
letting several individually acceptable archives into a workspace.

Final wall: `artifacts/line-2/wall-v11.png`, opaque RGB PNG, **1254 × 1254**.
Continuation: `artifacts/line-2/wall.png`, identical bytes.
Preview: `dist/line-2/30.jpg`, JPEG, **512 × 512**, **89,442 bytes**.
Record: `dist/line-2/30.json`; its image URL hashes the complete final PNG.
The required versioned PNG is left untracked for the daemon's separate upload.

Visual review: inspected the full finished wall and its final preview. The new
small prehistoric pigment mark occupies bare upper-right rock. A crooked branch
holds two woven bundles; the red ochre bundle hangs beside a yellow ochre bundle.
An uneven ochre curve above the branch ties the mark together. Only the new
pigment was composited; original rock grain and lighting remain visible.
The first palette used charcoal on dark stone and was hard to see at preview
size, so the same generated drawing was mapped to yellow ochre there. One
image was generated; no draft or cropped picture was saved in the workspace.

Existing Pepe retains his wide mouth and heavy-lidded eyes. Counted **five digits
on each existing hand**, four fingers and one thumb; neither hand changed.
No hands or handprints were added. No letters, numbers, captions, signatures,
logos, watermarks, borders, frames, real people or political/hateful symbols
were observed. No ancestral mark was erased, moved or redrawn.

Preservation: the predecessor matches record 29's SHA-256. Exactly **8,273
pixels** changed within x=[820,1060), y=[215,353); **zero outside** changed.
All earlier painted marks lie outside that patch. **1,564,243 pixels** remain
identical. Size, rock, cracks, framing, warm color and torchlight are preserved.
PNG decode/encode roundtrip and structural PNG/JPEG inspections passed.
See `media-check-30.json` for hashes, bounds and byte counts.

Unmet visual requirements: none observed in the new mark. Limitations: the
inherited rock has a photographic appearance, retained to preserve the wall;
the fine woven hatch marks soften at 512 pixels and the red sack has lower
contrast than the ochre sack. This is worker inspection, not independent art
approval. The explicitly required record-adjacent JPEG is delivered in dist/
despite the brief's conflicting general sentence about pictures in artifacts/.

Made the pigment with the built-in image generator, imported directly into the
required artifacts path. Streamed the crop and resize in memory with ffmpeg;
used the existing line-1/media PNG/JPEG codecs without modifying them.
`finish-wall-30.cjs` records that one-time assembly. Do not run it against the
finished output: its pigment input has been replaced with the complete wall.
All worker-facing ZIP tools remain Python standard library only.
