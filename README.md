# Metabase: ReadyStack build kit

The offline build kit for the Docker image `readystack/metabase:v0.65.6.4-CE-ubuntu24.04-r1`. It holds what the image is built from (upstream source, base images, toolchain, pinned dependencies) and the documents, so the image can be rebuilt with no network access (`docker build --network=none`).

- Release: [v0.65.6.4-CE-ubuntu24.04-r1](https://github.com/readystack-dev/metabase/releases/tag/v0.65.6.4-CE-ubuntu24.04-r1)
- Image: [`docker.io/readystack/metabase:v0.65.6.4-CE-ubuntu24.04-r1`](https://hub.docker.com/r/readystack/metabase/tags), manifest digest `sha256:248871c75ef9c0ca95bcb865113975e3d3e158ec9551db31c89ca05da8d7b078`
- Product page: https://readystack.dev/products/metabase
- Defects: this repository's Issues (defects recorded from 25 November 2026 on) and https://readystack.dev/defects.html?product=metabase

Metabase is distributed under its upstream licence (AGPL-3.0); the kit contains upstream's source under that licence, and each vendored component under its own.

## Download

From the [v0.65.6.4-CE-ubuntu24.04-r1 release](https://github.com/readystack-dev/metabase/releases/tag/v0.65.6.4-CE-ubuntu24.04-r1): `ReadyStack-metabase-v0.65.6.4-CE-ubuntu24.04-r1.tar.gz` (1.8 GB), SHA-256 `e2fef404155e51d936e7c3dafb3a5cbc6f2a5fc1b5eee0120fc206d3cf862a68`.

```sh
sha256sum --check --ignore-missing SHA256SUMS
```

## Verify and rebuild

The rebuild statement is signed with the ReadyStack release key. Check the signature before you rely on it:

```sh
cosign verify-blob --key https://readystack.dev/keys/cosign.pub \
  --bundle ReadyStack-metabase-v0.65.6.4-CE-ubuntu24.04-r1.rebuild.json.sigstore ReadyStack-metabase-v0.65.6.4-CE-ubuntu24.04-r1.rebuild.json
```

Unpack with `-p` so file modes are kept, then follow the kit's own README.md and docs/REBUILD.md:

```sh
tar -xpzf ReadyStack-metabase-v0.65.6.4-CE-ubuntu24.04-r1.tar.gz
cd v0.65.6.4-CE-ubuntu24.04-r1
less README.md docs/REBUILD.md
```

The build trail (`ReadyStack-metabase-v0.65.6.4-CE-ubuntu24.04-r1.trail.json`, signed the same way, and its Markdown copy) records how this release was built and checked.

## This repository

`recipe/` holds the kit's recipe files (Dockerfiles, build scripts, pins) as published at https://readystack.dev/products/metabase/recipe. The complete kit is the release download. Each release is a tag here.
