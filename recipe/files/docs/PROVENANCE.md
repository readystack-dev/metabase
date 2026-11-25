# Provenance — Metabase (`v0.65.7.1-CE-ubuntu24.04-r1`)

Every item below is copied from a record in this archive; the record is named in brackets.

## Source

- Upstream repository: https://github.com/metabase/metabase
- Revision built: `v0.65.7.1` (commit `b63429151e6bc66420dfdb6e3c5ceb973ca8a467`)
- Source tree: `b82595d32048337cf2f058c0792cb69767fa170f5aa152effa906aeca989575d` over 20064 files [`docs/provenance/SOURCE_TREE_HASH.json`]
- Community Edition only: enterprise code is removed or refused before the build (CE audit at acquire).

## Build

- Method: `source-rebuild-java`; base image `eclipse-temurin:25-jre-noble`
- Compiled with `--network=none` from vendored source, dependencies and base images; BuildKit pinned to `moby/buildkit:v0.31.2` (shipped in `toolchain/`).
- SOURCE_DATE_EPOCH: `1795590400` [`SOURCE_DATE_EPOCH.txt`]
- Frozen inputs: [`docs/provenance/FREEZE_MANIFEST.json`], build recipe: [`docs/provenance/BUILD_RECIPE.json`].

## Output

- Published image: `readystack/metabase:v0.65.7.1-CE-ubuntu24.04-r1` — index digest `sha256:b8b68bcc7a647ed7ae8dffd04f47de7a5307f078a656bc5adeff6e0695c81706` [`docs/provenance/LOCKED_DIGEST.txt`]
- linux/amd64 image digest `sha256:fade468d1b340f8593079d131c64e2fb3c04faa9762da3e8b59a16138cdebdd4` — reproduced from this archive before publishing [`docs/provenance/REPRO_VERIFICATION.json`].

## Attestations and signature

- SBOM + SLSA provenance attached to the image: attached: an SPDX SBOM and SLSA v1 provenance [`docs/provenance/SCOUT_VERDICT.json`]
- cosign signature by the ReadyStack release key: verified before publishing. Check it: `cosign verify --key https://readystack.dev/keys/cosign.pub readystack/metabase:v0.65.7.1-CE-ubuntu24.04-r1`

## Pinned inputs, and why

- 23 pinned inputs, each with where it came from, why this one, how it was checked and when it was decided: `docs/PINS.md` [`docs/provenance/PINS.json`] (upstream source 2, base and build images 3, image digests 2, language runtimes and toolchains 5, dependency versions readystack sets 3, pins in the kit's dockerfiles 6, readystack's build engine 1, dependencies upstream chose 1).

## Build trail

- How this release passed through the ReadyStack harness, record by record (every chain, drive, stage, review round, defect and check, each naming the record it is copied from): `ReadyStack-metabase-v0.65.7.1-CE-ubuntu24.04-r1.trail.json`, published beside this archive and signed with the release key (`ReadyStack-metabase-v0.65.7.1-CE-ubuntu24.04-r1.trail.json.sigstore`), and readable at https://readystack.dev/products/metabase/trail/v0.65.7.1-CE-ubuntu24.04-r1.

