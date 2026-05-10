# overlay/ — JuiceLab files to copy into a vanilla Juice Shop tree

This folder is a **mirror** of the JuiceLab additions to OWASP Juice Shop. Every path here maps 1:1 to a path inside `juice-shop/`.

The structure is :

```
overlay/
├── data/
│   └── juicelab-private/             111 YAML packs (hints, quiz, walkthroughs)
├── frontend/
│   └── src/
│       ├── app/
│       │   └── juicelab-overlay/     18-file Angular standalone overlay
│       └── assets/
│           └── juicelab/             public briefings, config, selected_challenges
└── routes/
    └── juicelab.ts                   Express route with anti-leak gating
```

Total : 365 files, ~ 2.9 MB on disk.

## How it is applied

`scripts/apply-overlay.sh` (or `.ps1` on Windows) copies every file in this tree on top of a vanilla OWASP Juice Shop clone, then applies `patches/juicelab-core.patch` to wire the overlay into the Juice Shop core (server route, navbar entry, score-board card, i18n keys, config flag).

```bash
git clone https://github.com/juice-shop/juice-shop.git ../juice-shop
./scripts/apply-overlay.sh ../juice-shop
```

See [`INSTALL.md`](../INSTALL.md) for the full procedure.

## What is in here vs what is patched

| Operation | Where | Files |
|---|---|---|
| **Copy (new files)** | this `overlay/` folder | The overlay code, the private packs, the public assets, the new Express route |
| **Patch (existing files)** | `patches/juicelab-core.patch` | `config/default.yml`, `server.ts`, the score-board card, navbar, sidenav, app.routing, i18n EN/FR, ftp acquisitions, frontend package.json |

Anything that has never existed in upstream Juice Shop lives here. Anything that does exist upstream and only needs a small modification lives in the patch.

## Why this structure

* **Reproducibility.** A `git clone` of the upstream OWASP repo + this overlay + this patch always produces the same working tree. No hidden state in the maintainer's environment.
* **Upstream tracking.** When OWASP releases a new Juice Shop, we re-base our patch against the new upstream and bump the overlay version. Files unchanged upstream stay unaffected ; conflicts surface in `git apply --check`.
* **Auditability.** A teacher reviewing JuiceLab can `diff` this folder against their installation to confirm no tampering. Every file here is part of the public license, no opaque artifact.

## What is NOT in here

* The OWASP Juice Shop sources themselves. They live upstream at <https://github.com/juice-shop/juice-shop> and are 1.2 GB with `node_modules/`.
* The Flask dashboard. That is its own service, see [`dashboard/`](../dashboard/).
* The Docker Compose stack. See [`docker/`](../docker/).
* The `juice.ps1` Windows launcher. See the repo root.

## Updating the overlay

When you change a file inside the overlay, the change must propagate :

1. Edit the file under `overlay/...`.
2. Re-run `scripts/apply-overlay.sh ../juice-shop` so your working `juice-shop/` clone gets the new version.
3. Restart the Juice Shop container (`docker compose restart juicelab-demo`) or the dev server (`npm start`).
4. Commit your overlay change to this repo.

When you change a file that exists upstream (anything covered by `patches/juicelab-core.patch`), update the patch :

1. Edit the file in your working `juice-shop/` clone.
2. From the Juice Shop directory, regenerate the patch :
   ```bash
   git diff origin/master -- ':!frontend/src/app/juicelab-overlay/services/juicelab-sync.service.ts' \
       > ../patches/juicelab-core.patch
   ```
3. Commit the updated patch to this repo.

The exclusion of `juicelab-sync.service.ts` is because that file is part of the overlay (it lives in `overlay/frontend/src/app/juicelab-overlay/services/`), so it must be copied, not patched.
