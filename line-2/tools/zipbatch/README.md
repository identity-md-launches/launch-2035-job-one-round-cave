# ZipBatch

Plan several complete ZIP extractions against **one shared budget** before
creating any output trees. Two archives that each fit alone can still exceed a
worker's allowance together. ZipBatch checks each approved archive's complete
payload through the existing ZipGate and SafeZip engines, then sums entries,
file bytes and filesystem nodes across separate intended output trees.
Python 3.9+ standard library only; no install or network required.

From the repository root, one command demonstrates it:

```sh
python3 -B line-2/tools/zipbatch/demo.py
```

Tried here: replayed the historical public IMD OpenAPI capture already shipped
at `../safezip/imd-openapi.json` (source provenance beside it). Two illustrative
ZIP packages each contain that genuine 23,132-byte capture. Each fits a
23,132-byte allowance alone; together the planner refuses that allowance.
With 46,264 bytes, two entries and eight nodes it accepts exactly. Eight means
two separate roots, four implicit directories and two files. No archive was
extracted and no public endpoint was contacted. The demo makes and removes
its disposable ZIPs under `test/scratch/`.

## Use

Inspect/review your ZIPs first and retain their actual SHA-256 digests. Pass one
approval per archive in matching order (the first hash approves the first path):

```sh
python3 -B line-2/tools/zipbatch/zipbatch.py --archive first.zip --sha256 FIRST_REVIEWED_DIGEST --archive second.zip --sha256 SECOND_REVIEWED_DIGEST --batch-bytes 67108864 --batch-nodes 32000 --batch-entries 1000 --seconds 10
```

The two uppercase digest labels above are documentation placeholders: replace
them with your actual reviewed 64-hex digests. The planner refuses missing,
invalid and mismatched approvals. The Python API accepts a nonempty list/tuple:

```python
from zipbatch import plan
report = plan([
    {"archive": "first.zip", "sha256": first_reviewed_digest},
    {"archive": "second.zip", "sha256": second_reviewed_digest},
], batch_bytes=67108864, batch_nodes=32000, seconds=10)
```

Each declaration must have exactly those two keys. All declarations and paths
are validated before archive inspection. The API raises `Rejected` for policy
refusals; I/O/ZIP errors may propagate. CLI success is JSON and exit 0. Policy,
I/O or corruption failure is `{"ok": false, "error": "..."}` and exit 2;
argument syntax failures use argparse stderr and exit 2. There is no partial
success report if a later archive fails. The report contains per-archive digests,
counts, pre-parser gate results, totals and the batch limits.

## Accounting and limits

These positive-integer batch limits have defaults:

| Flag | Default | What it bounds |
| --- | ---: | --- |
| `--batch-archives` | 32 | Number of intended separate extractions |
| `--batch-entries` | 1000 | Sum of explicit directory/file ZIP entries |
| `--batch-nodes` | 32000 | All distinct tree nodes, including each output root |
| `--batch-bytes` | 67108864 | Sum of uncompressed file bytes |

Implicit parents count once **within each archive**. Empty explicit directories
count; each output root counts even for an empty ZIP. Repeated archives count
repeatedly, as do matching paths in different archives. This models separate
complete output trees, never an overlay or merged extraction. Empty archives
and zero-byte files may fit after the file-byte allowance is exhausted.

Per-archive flags are `--entries` (1000), `--directory-bytes` (2097152),
`--archive-bytes` (33554432), `--nodes` (32000, excluding its root),
`--file-bytes` (16777216), `--total-bytes` (67108864) and `--ratio` (200).
The remaining shared entry/node/byte allowance tightens the next inspection.
The inherited gate bounds central-directory allocation before ZIP parsing.
Every payload is streamed, hashed and CRC checked, even though nothing is
extracted. Only summaries survive between archives; inventories are bounded
by the per-archive and remaining shared limits.

Archive input bytes have a **per-archive** limit; the batch input volume is
bounded by `batch_archives * archive_bytes`, with multiple bounded read passes
per archive inherited from ZipGate. Batch bytes are logical payload bytes,
not filesystem block use, compressed input storage, free space or peak RAM.
Small files, metadata, staging and source ZIP retention can require more disk.
No disk-space query or reservation is made.

`--seconds` is one finite positive cooperative deadline for the entire plan,
including all inherited inspections and accounting. The API also accepts a
fast side-effect-free `cancelled` callback. Neither starts a timer or sleeps.
A blocking filesystem/parser/decompression call can exceed the deadline;
serialization is outside it. This is not a hard CPU or memory sandbox.

## Limits of the result

The planner reads workspace files only; every existing symlink component is
refused. Use a cooperative local workspace without concurrent mutation: the
inherited tools do not defend against hostile rename/symlink races. ZIP64,
prefixes and some valid classic layouts are conservatively unsupported.
Digest identity establishes neither publisher trust nor content safety.

This is a read-only plan, not an extractor, disk reservation or durable promise.
Before later extraction, run ZipGate's `extract` on each archive into its own
absent output root with the same approved digest and reviewed limits. Recheck
if the batch or policy changes. A saved JSON report is never authorization to
skip those checks. Nothing signs, sends, pays, deploys, opens a wallet, reads
environment variables or executes archive content. No coin is needed.

## Checks

```sh
python3 -B line-2/tools/zipbatch/selftest.py
```

Observed **30 tests passed**, covering exact combined boundaries, aggregate
entries/bytes/nodes, empty archives and exhausted allowances, implicit parents,
repeated inputs, mandatory approvals, pre-I/O declaration checks, all invalid
limits, shared deterministic deadline/cancellation without sleeps, inherited
budgets, traversal and symlink refusal, corrupted CRC and CLI results. The
**162 inherited tests** also passed unchanged. These are local observations.
