# Provenance — Metabase (`v0.65.6.4-CE-ubuntu24.04-r1`)

Every item below is copied from a record in this archive; the record is named in brackets.

## Source

- Upstream repository: https://github.com/metabase/metabase
- Revision built: `v0.65.6.4` (commit `eae4af03094e1f8ad7b7ecfcba73189c5014013c`)
- Source tree: `f43c30923b064edb62497bf7428b9cad48a46f4f7c0754bbdcc5210f8034a529` over 20069 files [`docs/provenance/SOURCE_TREE_HASH.json`]
- Community Edition only: enterprise code is removed or refused before the build (CE audit at acquire).

## Build

- Method: `source-rebuild-java`; base image `eclipse-temurin:25-jre-noble`
- Compiled with `--network=none` from vendored source, dependencies and base images; BuildKit pinned to `moby/buildkit:v0.31.2` (shipped in `toolchain/`).
- SOURCE_DATE_EPOCH: `1795543240` [`SOURCE_DATE_EPOCH.txt`]
- Frozen inputs: [`docs/provenance/FREEZE_MANIFEST.json`], build recipe: [`docs/provenance/BUILD_RECIPE.json`].

## Output

- Published image: `readystack/metabase:v0.65.6.4-CE-ubuntu24.04-r1` — index digest `sha256:09dc310161b4c5332b0db47128c83ec51044b4419b38c41ae1c914d47dba50bd` [`docs/provenance/LOCKED_DIGEST.txt`]
- linux/amd64 image digest `sha256:248871c75ef9c0ca95bcb865113975e3d3e158ec9551db31c89ca05da8d7b078` — reproduced from this archive before publishing [`docs/provenance/REPRO_VERIFICATION.json`].

## Attestations and signature

- SBOM + SLSA provenance attached to the image: attached: an SPDX SBOM and SLSA v1 provenance [`docs/provenance/SCOUT_VERDICT.json`]
- cosign signature by the ReadyStack release key: verified before publishing. Check it: `cosign verify --key https://readystack.dev/keys/cosign.pub readystack/metabase:v0.65.6.4-CE-ubuntu24.04-r1`

## Pinned inputs, and why

- 23 pinned inputs, each with where it came from, why this one, how it was checked and when it was decided: `docs/PINS.md` [`docs/provenance/PINS.json`] (upstream source 2, base and build images 3, image digests 2, language runtimes and toolchains 5, dependency versions readystack sets 3, pins in the kit's dockerfiles 6, readystack's build engine 1, dependencies upstream chose 1).

## Build trail

- How this release passed through the ReadyStack harness, record by record (every chain, drive, stage, review round, defect and check, each naming the record it is copied from): `ReadyStack-metabase-v0.65.6.4-CE-ubuntu24.04-r1.trail.json`, published beside this archive and signed with the release key (`ReadyStack-metabase-v0.65.6.4-CE-ubuntu24.04-r1.trail.json.sigstore`), and readable at https://readystack.dev/products/metabase/trail/v0.65.6.4-CE-ubuntu24.04-r1.

