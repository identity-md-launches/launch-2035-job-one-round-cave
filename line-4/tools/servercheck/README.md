# ServerCheck

Find potential destination breaks before upgrading an OpenAPI integration. Python 3.9+, standard library only, no installation or network needed. From the repository root:

```sh
python3 -B line-4/tools/servercheck/servercheck.py demo
```

The working demonstration uses the bundled real public IMD description. It hypothetically migrates one operation to an illustrative `example.invalid` server in memory, finds one potential destination removal and two reviews across five operations, and exits 0. That address is never contacted. This is an analysis example, not an unsigned or live operation.

Compare your own workspace JSON descriptions:

```sh
python3 -B line-4/tools/servercheck/servercheck.py compare line-4/tools/apidelta/imd-openapi.json line-4/tools/apidelta/imd-openapi.json
```

Output is deterministic JSON with input-byte SHA-256 hashes. Compare exits: 0 no detected break, 1 potential break, 2 refused/error, 3 unresolved review. Keep all sibling analyzers from ApiDelta through OAuthCheck; ServerCheck imports them by explicit workspace paths and retains their findings. No external dependency, environment/configuration read, credential, endpoint probing, transaction or deployment is needed. API compatibility analysis needs no coin.

## Rules

For each common operation, choose operation servers before path servers before root servers. A missing or empty **root** array defaults to `/`. An explicitly empty path/operation array is refused rather than guessed to mean inheritance or a default. Validate effective declarations even when identical. Shadowed declarations and operations only present on one side are outside this extension's validation; earlier rules still report operation addition/removal.

Literal URLs and templates whose used variables all have enums produce finite sets of literal destination references. Every old finite destination must remain in the union of new finite destinations. Missing entries produce `server_destination_removed` potential breaks. Repeated occurrences of a variable use the same selected value; substitution is simultaneous and does not recursively interpret values. Server order, duplicate entries, and different template spellings that expand to the same finite references do not create destination removals. Earlier metadata reviews may remain.

A variable without an enum has an open domain: it is **not** restricted to its default. If any new effective server has such a variable, missing finite references are unresolved reviews rather than definite finite-domain removals. Old open templates need identical URL spelling and used variable names/domains in the new open declarations; otherwise they produce a template coverage review. This deliberately incomplete rule does not attempt arbitrary template-language containment. Changes to the set of default-substituted references produce a separate review, including when available enum choices survive.

The implementation follows the [OpenAPI 3.1 Server and Server Variable Objects](https://spec.openapis.org/oas/v3.1.0.html#server-object), including required defaults and membership of defaults in enums. It handles the same supported OpenAPI 3.0.x/3.1.x inputs as the earlier pipeline.

## Bounds and limitations

Effective arrays have at most 64 servers, at most 32 variables per server and 256 choices per enum. Each finite server expands to at most 256 combinations. URL templates and substitution values have at most 4096 characters; expanded/default references have at most 8192. Finite expansions use at most 2 Mi characters per effective array and 8 Mi characters across cached arrays, plus a 100,000 expansion work limit. Exhaustion refuses the comparison without returning a partial compatibility pass. Used variable defaults must be strings; enums must be nonempty string arrays containing the default. Whitespace, control characters and braces in substitution values are conservatively unsupported. References in Server Objects are refused; unused variable definitions are not validated.

Input limits remain 1 MiB, 50,000 nodes, depth 80, 20,000 schema visits and 2,000 findings, with earlier security comparison bounds. References are compared literally: no URL normalization, document-location base, redirects, DNS, reachability, actual host behavior, generated client behavior or discovery is checked. Server order changes receive inherited reviews rather than a claim about default selection. No additional URL syntax validation is claimed. The inherited JSON float precision limitation remains for numeric schema checks. A clean report is not proof of runtime compatibility; a breaking report describes a potential integration failure.

## Tried

- `python3 -B line-4/tools/servercheck/selftest.py`: 15 tests passed, including 49 finite-domain pairs checked against an independent set oracle and explicit literal-server representations, precedence, root defaults, repeated variables, multiple variables, open domains, default changes, malformed identical declarations, shadowing, budgets, inherited finding retention, nonmutation, determinism, pointer escaping and all CLI outcomes.
- `python3 -B line-4/tools/oauthcheck/selftest.py`: 16 unchanged regression tests passed.
- Demo: five operations, one potential break, two reviews, successful demo exit.
- A read-only GET of `https://api.imd.fun/openapi.json` using User-Agent `Pepeolithic-ServerCheck/30.0` matched the bundled capture: SHA-256 `be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a`. Five operations compared with zero findings. No described API operation was executed.

Evidence: `line-4/check-results-30.json`; saved public input: `line-4/live-openapi-30.json`. Reproduce offline checks with `python3 -B line-4/check-30.py`; optional `--live` repeats the public description GET.
