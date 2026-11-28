# Metabase v0.65.7.4 — ReadyStack release `v0.65.7.4-CE-ubuntu24.04-r1`

Generated 2026-11-28 from this release's build records and strategy. Statements that come from a single record name it in brackets; the others come from this release's strategy and build log.

## Release

- **Image:** `readystack/metabase:v0.65.7.4-CE-ubuntu24.04-r1` (linux/amd64). Index digest `sha256:83faabea21b07b28750f40a5feed724d98ce4eb9358ba52ca15691c4d64f2b53` [`docs/provenance/LOCKED_DIGEST.txt`].
- **Image manifest digest:** `sha256:547ba779f4e5cefb18a04ba9d880b45fd6f2a08d97ced2410a0e4be282ac9cf3` [`TARGET_DIGEST.txt`].
- **Upstream:** Metabase v0.65.7.4 built from source at `v0.65.7.4` of https://github.com/metabase/metabase — upstream notes: https://github.com/metabase/metabase/releases/tag/v0.65.7.4 [`docs/provenance/BUILD_RECIPE.json`].
- **Base image:** `eclipse-temurin:25-jre-noble`; runtime user `metabase`.
- **Build:** `source-rebuild-java`, compiled offline with `--network=none`.
- **Supersedes:** ReadyStack release `v0.65.7.1-CE-ubuntu24.04-r1`.

## What changed in this release

- Upstream version v0.65.7.1 → v0.65.7.4.
- This release moves Metabase from 0.65.7.1, which the release this supersedes (v0.65.7.1-CE-ubuntu24.04-r1) packaged, to 0.65.7.4, a newer release of upstream's 0.65.x line. Upstream's release notes list what changed: https://github.com/metabase/metabase/releases/tag/v0.65.7.4

## Security status at release (measured 2026-11-28)

- **Docker Scout:** 0 fixable critical/high vulnerabilities; runs as `metabase` (non-root); SBOM + provenance attestations present (SPDX SBOM + SLSA v1) [`docs/provenance/SCOUT_VERDICT.json`].
- **OSV cross-check:** no fixable critical/high vulnerability beyond Docker Scout's findings.
- **Signature:** cosign signature verified by ReadyStack's release gate before publishing; check it yourself with `cosign verify --key https://readystack.dev/keys/cosign.pub readystack/metabase:v0.65.7.4-CE-ubuntu24.04-r1` (signatures are recorded in the public Sigstore transparency log).
- **ReadyStack release check at release:** passed (ReadyStack's own test, not a Docker Scout grade). Vulnerabilities are disclosed every day and the image never changes, so it is re-checked daily, beside Docker Scout's own dated grade, at https://readystack.dev/queue.

## Reproducibility

Rebuilds offline from this archive to the identical image digest `sha256:547ba779f4e5cefb18a04ba9d880b45fd6f2a08d97ced2410a0e4be282ac9cf3`: run `./BUILD_OFFLINE.sh`, then `./VERIFY_OFFLINE.sh` (add `--online` to confirm the Docker Hub tag holds the same digest). Before publishing, ReadyStack rebuilt the kit with `./BUILD_OFFLINE.sh` and compared the result with the published digest [`docs/provenance/REPRO_VERIFICATION.json`], then ran `./BUILD_OFFLINE.sh` and `./VERIFY_OFFLINE.sh` from this archive (without `--online`).

## Validation

- 5 of 5 use cases passed (5 authored) against the running image [`docs/validation/test-results.json`].

## Known issues

- None found (reviewed by held semantic review (Claude) on 2026-11-28).

## Differences from upstream (by design)

- Enterprise / non-open-source components are removed from the source before the build: enterprise, LICENSE-MCL.txt [`RSD-metabase-649e40f3f6`]

## Defects fixed

- 1 problem found before release and fixed before it shipped (1 by review); each is listed in `docs/defects/defects.json`.

## Verify this archive

```
sha256sum -c CHECKSUMS.sha256
./BUILD_OFFLINE.sh && ./VERIFY_OFFLINE.sh --online
cosign verify --key https://readystack.dev/keys/cosign.pub readystack/metabase:v0.65.7.4-CE-ubuntu24.04-r1
```

ReadyStack records every signature in the public Sigstore transparency log (Rekor), so the command needs no extra flags.

