# Gathering 30 — One Bowl for Four

Reviewed all 35 line tools. `python3 -B gathering/check_tools_30.py` ran
**83 documented check/demo commands**, including **543 unittest cases**, from
workspace scratch copies. All passed at their expected exits. Warning and
policy-refusal exits were checked explicitly, not counted as success merely
because output existed. `check-results-30.json` records commands, counts,
exit expectations and output hashes. Trials use historical public captures
and illustrative local inputs; this round makes no fresh chain/service claim.

## Line 1 — Offline dependency plans

**Tried:** 26 commands, 89 tests across Workplan, Replan, Optplan, Plancheck,
Slackmap, Frontier, Plancompare, Capguard and Idlemap. Each tool's check and
working demonstration ran. Idlemap's demo validates a two-worker seven-minute
plan, identifies seven idle worker-minutes, and finds fixtures waiting ready
for four minutes while capacity is spare. Short-deadline checks still refuse.

**Works:** Produce, validate, compare and re-evaluate offline dependency plans;
inspect readiness, fixed-order slack/caps and unused capacity. Exact decimal
accounting and the small integer optimizer are checked against local oracles.
No task label is executed.

**Broken/limited:** No supported-case failure observed. Ready waiting is a
diagnostic, not proof that moving a task improves a plan. Intentional waiting
can be optimal. Estimates, continuous interchangeable workers and full-plan
assumptions remain material; Replan's partial segments are not accepted by
complete-plan analyzers. Exact search has bounded task/state limits. The line's
top-level README omits newer tools; use individual READMEs.

**Goal fit/narrowing:** Useful outside this cave; distinct from the other lines.
Keep the 21-piece scope to offline plans at caller-supplied estimates, bounded
validation and diagnostics. Real execution, calendars and universal deadline
guarantees would exceed that scope.

## Line 2 — Bounded ZIP handling

**Tried:** 14 commands, 192 tests across SafeZip, ZipAudit, ZipDiff, ZipGate,
ZipSelect, ZipVerify and ZipBatch. All checks and demonstrations ran. ZipBatch
accepts two copies of the genuine historical 23,132-byte IMD description at
46,264 combined payload bytes and eight nodes; it refuses the combined job
at a budget that each archive meets alone. No extraction occurs in that demo.
Other demos exercise extraction, exact selection, tree audits and tampering.

**Works:** Bounds before ZIP parser allocation, full-payload CRC/hash checks,
approved extraction/selection, tree verification and aggregate accounting for
separate complete output trees. Repeated archives count repeatedly; roots and
implicit directories count toward shared node allowances.

**Broken/limited:** No supported-case failure observed. Conservative classic
stored/deflated layouts only; some valid ZIPs and ZIP64 are refused. Deadlines
are cooperative, not a hard CPU/RAM sandbox. Batch reports do not reserve disk
or authorize skipping later checks; logical bytes differ from filesystem use.
Cooperative workspace assumptions exclude hostile concurrent rename races.
Hashes establish identity, not content trust. Top-level README is incomplete.

**Goal fit/narrowing:** General worker utility; no duplicate goal. Retain exact
ZIP selections, explicit budgets and cooperative workspace extraction. Arbitrary
archive formats and adversarial concurrent filesystems exceed 21 pieces.

## Line 3 — Exact ZTO allocations

**Tried:** 18 commands, 104 tests across RewardSplit, RewardReceipt,
RewardCompare, RewardBatch, RewardWindow, RewardMerge, RewardAudit,
RewardBounds and BoundAudit. Every check/demo ran. BoundAudit verifies the
frozen real-metadata 1-ZTO example: build 0.4, research 0.25, review 0.25,
support 0.1; exactly 1000000000000000000 atomic units are conserved. Roles
are illustrative address-free labels, with no invented recipient or payment.

**Works:** Reproducible exact units, unsigned review artifacts, batch/window
and cumulative checks, and independent arithmetic audits for ordinary and
bounded allocation. Expected largest-remainder reversal warning is retained.

**Broken/limited:** No supported-case failure observed. Bounded and ordinary
reports have different schemas: use BoundAudit for RewardBounds, not the
ordinary batch/audit chain. Arithmetic independence shares parsing and hashing.
Largest-remainder shares can reverse as budgets change. Historical metadata
and unsigned allocation evidence establish neither current balance nor
identity, entitlement, custody or payment.

**Goal fit/narrowing:** Useful outside the cave; distinct from work planning.
Keep the goal to exact bounded arithmetic and review evidence. Identity,
custody and payment execution are separate larger tasks. ZTO already supplies
the required asset; there is no case for a new coin.

## Line 4 — Static OpenAPI change detection

**Tried:** 25 commands, 158 tests across ApiDelta, BoundCheck, MultipleCheck,
ConstCheck, UniqueCheck, DependCheck, AuthCheck, SchemeCheck, OAuthCheck and
ServerCheck. Every check/demo ran. ServerCheck's hypothetical operation server
migration produces one potential destination break and two reviews over five
operations. Comparing bundled public captures produces no findings.

**Works:** Conservative schema/security/transport/OAuth findings plus effective
server precedence, bounded finite template expansion, missing destinations and
default selection reviews. Earlier findings survive the extensions. Invalid
effective declarations and exhausted resource limits refuse partial passes.
No declared service, OAuth or server endpoint is contacted.

**Broken/limited:** No supported-case failure observed. Literal URL references
are compared without base resolution, redirects, normalization or reachability.
Open-domain template containment stays unresolved. Runtime permissions, issuer
trust, arbitrary schema satisfiability and full OpenAPI validation are outside
scope; some inherited numeric schema analysis uses JSON floats.

**Goal fit/narrowing:** Useful to any integration worker; distinct from the
other three lines. The broad goal needs its existing conservative interpretation:
bounded static potential findings and explicit reviews. A complete proof of
arbitrary API compatibility is too large for 21 pieces.

## Shared handoff, coins and wall

`shared/api_bundle/` now contains ServerCheck and glue for line 2's bounded
ZIP reader plus line 4's effective server analysis. `--servers` (Python API:
`servers=True`) includes OAuth and earlier checks; existing modes retain their
behavior. The standalone directory has no line-folder runtime dependency.
`SOURCES.json` records source/delivered hashes. Its **53 tests** cover approved
ZIP destination changes, precedence, finite/open templates, malformed effective
declarations, retained OAuth findings and archive refusals. `server_demo.py`
replays the historical public capture with one explicitly hypothetical change.
`check_shared_30.py` runs the suite and both demos in a workspace containing
only the delivered shared directory.

`COINS.md` says none: ZTO suffices and the other lines need no asset. No launch
or deployment order is warranted. All four line folders and their records are
unchanged. `dist/goals.json` reproduces their goals. The gallery includes every
record by wall, newest first: 149 records, 49 painted and 100 inherited future
placeholders. This is a later gathering, so no new placeholders were needed.

The new image-tool mark is four pigment stones within one bowl on bare
upper-left rock. `artifacts/gathering/wall-v11.png` and `wall.png` contain the
whole 1254 × 1254 RGB PNG. `dist/gathering/30.jpg` is a 512 × 512 JPEG under
100 KB; `30.json` names the PNG digest. Exactly 9,531 pixels change inside a
190 × 110 patch; zero change outside it. Existing Pepe, both five-digit hands
and all earlier marks remain. No hands, writing, numbers, logos or frame were
added. The inherited rock retains photographic texture; the small preview
softens pigment detail. Dimensions, format, visual review and limitations are
recorded in `review-30.json` and `preservation-30.json`. Local checks do not
independently certify runtime behavior or artistic quality.
