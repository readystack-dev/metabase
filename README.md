# Metabase: ReadyStack build kit

The offline build kit for the Docker image `readystack/metabase:v0.65.7.1-CE-ubuntu24.04-r1`. It holds what the image is built from (upstream source, base images, toolchain, pinned dependencies) and the documents, so the image can be rebuilt with no network access (`docker build --network=none`).

- Release: [v0.65.7.1-CE-ubuntu24.04-r1](https://github.com/readystack-dev/metabase/releases/tag/v0.65.7.1-CE-ubuntu24.04-r1)
- Image: [`docker.io/readystack/metabase:v0.65.7.1-CE-ubuntu24.04-r1`](https://hub.docker.com/r/readystack/metabase/tags), manifest digest `sha256:fade468d1b340f8593079d131c64e2fb3c04faa9762da3e8b59a16138cdebdd4`
- Product page: https://readystack.dev/products/metabase
- Source and build recipe: https://readystack.dev/products/metabase/recipe
- Build trail: https://readystack.dev/products/metabase/trail/v0.65.7.1-CE-ubuntu24.04-r1
- Defects: this repository's Issues (defects recorded from 25 November 2026 on) and https://readystack.dev/defects.html?product=metabase

## The image

Single container, SELF-CONTAINED. A JVM (Clojure) business-intelligence / analytics server (dashboards, 'questions', SQL editor) shipped as one self-contained uberjar (metabase.jar) on an eclipse-temurin 25 JRE. The application database defaults to an EMBEDDED H2 file the container creates + Liquibase-migrates itself on first boot — the image IS the complete running instance (NO external DB, NO sidecar, NO docker-compose required). For production scale Metabase can OPTIONALLY be pointed at an external PostgreSQL/MySQL application database via MB_DB_TYPE + MB_DB_* env vars, but that is optional; the default and certified single-container posture is embedded H2, but Metabase logs a warning at every start that H2 is not recommended for production, so back up /metabase-data regularly.

## Who uses Metabase and why

Companies that want everyone, not only analysts, to ask questions of their data.

Metabase is an open-source business intelligence tool. People explore data and build charts and dashboards without knowing SQL, and analysts use its SQL editor for more complex queries.

A typical use: A start-up's product data sits in its application database and only engineers can query it. With Metabase connected to that database, the support lead charts tickets per customer without writing SQL, and the finance team gets a dashboard with filters it checks each week.

From the upstream project's own description: https://github.com/metabase/metabase.

## This release

- Docker Scout policy grade at release: **A** (94%), graded 2026-11-25 with `docker scout policy` (CLI 1.26.0, docker-default configuration).
  - Docker Scout counts 109 packages with copyleft licences (GPL, LGPL, MPL), 107 of them operating-system packages (it counts only packages whose licence it can read; the SBOM lists every component).
- Signed with ReadyStack's release key (fingerprint `04daa92344a52dbc`): https://readystack.dev/keys/cosign.pub.
- Runs as a non-root user (`metabase`).
- Attestations on the image: an SPDX SBOM and SLSA provenance v1.
- Rebuilt from this kit with network egress blocked on 2026-11-25; the rebuilt image digest is the published one.
- Base: Ubuntu 24.04.

The current grade, measured again every day, is on https://readystack.dev/products/metabase.

Metabase is distributed under its upstream licence (AGPL-3.0); the kit contains upstream's source under that licence, and each vendored component under its own.

## Download

From the [v0.65.7.1-CE-ubuntu24.04-r1 release](https://github.com/readystack-dev/metabase/releases/tag/v0.65.7.1-CE-ubuntu24.04-r1): `ReadyStack-metabase-v0.65.7.1-CE-ubuntu24.04-r1.tar.gz` (1.8 GB), SHA-256 `e07fd7fa6b01a7a1039653f03715c567b055f6bdf7cf08b055b8e21e65b4ef24`.

```sh
sha256sum --check --ignore-missing SHA256SUMS
```

## Verify and rebuild

The rebuild statement is signed with the ReadyStack release key. Check the signature before you rely on it:

```sh
cosign verify-blob --key https://readystack.dev/keys/cosign.pub \
  --bundle ReadyStack-metabase-v0.65.7.1-CE-ubuntu24.04-r1.rebuild.json.sigstore ReadyStack-metabase-v0.65.7.1-CE-ubuntu24.04-r1.rebuild.json
```

Unpack with `-p` so file modes are kept, then follow the kit's own README.md and docs/REBUILD.md:

```sh
tar -xpzf ReadyStack-metabase-v0.65.7.1-CE-ubuntu24.04-r1.tar.gz
cd v0.65.7.1-CE-ubuntu24.04-r1
less README.md docs/REBUILD.md
```

The build trail (`ReadyStack-metabase-v0.65.7.1-CE-ubuntu24.04-r1.trail.json`, signed the same way, and its Markdown copy) records how this release was built and checked.

## This repository

`recipe/` holds the kit's recipe files (Dockerfiles, build scripts, pins) as published at https://readystack.dev/products/metabase/recipe. The complete kit is the release download. Each release is a tag here.

— ReadyStack · https://readystack.dev
