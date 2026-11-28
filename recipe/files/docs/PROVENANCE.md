# Provenance — Metabase (`v0.65.7.4-CE-ubuntu24.04-r1`)

Every item below is copied from a record in this archive; the record is named in brackets.

## Source

- Upstream repository: https://github.com/metabase/metabase
- Revision built: `v0.65.7.4` (commit `615478ea918fa1488412a846f0380609d7f3d54b`)
- Source tree: `bc9cd78b4e7612ed25c8228d051af90d19c31a2f7b08bf1224400eb47a726ada` over 20068 files [`docs/provenance/SOURCE_TREE_HASH.json`]
- Community Edition only: enterprise code is removed or refused before the build (CE audit at acquire).

## Build

- Method: `source-rebuild-java`; base image `eclipse-temurin:25-jre-noble`
- Compiled with `--network=none` from vendored source, dependencies and base images; BuildKit pinned to `moby/buildkit:v0.31.2` (shipped in `toolchain/`).
- SOURCE_DATE_EPOCH: `1795849182` [`SOURCE_DATE_EPOCH.txt`]
- Frozen inputs: [`docs/provenance/FREEZE_MANIFEST.json`], build recipe: [`docs/provenance/BUILD_RECIPE.json`].

## Output

- Published image: `readystack/metabase:v0.65.7.4-CE-ubuntu24.04-r1` — index digest `sha256:83faabea21b07b28750f40a5feed724d98ce4eb9358ba52ca15691c4d64f2b53` [`docs/provenance/LOCKED_DIGEST.txt`]
- linux/amd64 image digest `sha256:547ba779f4e5cefb18a04ba9d880b45fd6f2a08d97ced2410a0e4be282ac9cf3` — reproduced from this archive before publishing [`docs/provenance/REPRO_VERIFICATION.json`].

## Attestations and signature

- SBOM + SLSA provenance attached to the image: attached: an SPDX SBOM and SLSA v1 provenance [`docs/provenance/SCOUT_VERDICT.json`]
- cosign signature by the ReadyStack release key: verified before publishing. Check it: `cosign verify --key https://readystack.dev/keys/cosign.pub readystack/metabase:v0.65.7.4-CE-ubuntu24.04-r1`

## Pinned inputs, and why

- 23 pinned inputs, each with where it came from, why this one, how it was checked and when it was decided: `docs/PINS.md` [`docs/provenance/PINS.json`] (upstream source 2, base and build images 3, image digests 2, language runtimes and toolchains 5, dependency versions readystack sets 3, pins in the kit's dockerfiles 6, readystack's build engine 1, dependencies upstream chose 1).

## Build trail

- How this release passed through the ReadyStack harness, record by record (every chain, drive, stage, review round, defect and check, each naming the record it is copied from): `ReadyStack-metabase-v0.65.7.4-CE-ubuntu24.04-r1.trail.json`, published beside this archive and signed with the release key (`ReadyStack-metabase-v0.65.7.4-CE-ubuntu24.04-r1.trail.json.sigstore`), and readable at https://readystack.dev/products/metabase/trail/v0.65.7.4-CE-ubuntu24.04-r1.

