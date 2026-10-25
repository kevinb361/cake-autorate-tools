# Provenance

Every file here comes from wanctl (GPL-2.0) unless it is listed as new. "Source sha256" is the first 12 hex digits of
the SHA-256 of the source file at the named wanctl commit:

- `7677720f` is wanctl main, `7677720f1b123512b6a59ec6f271338c851064cf`.
- `13b1cf44` and `e4a6115d` are earlier wanctl commits. Four files come from them:
  - the shadow analyzer (13b1cf44) and the rrul-slot timer (e4a6115d) are the versions that were actually installed
    when this repository was cut on 2026-10-25. The installed copies were hash-checked against these blobs before
    extraction;
  - the analyzer's test and `docs/RRUL_SLOT.md` were taken from 13b1cf44 to stay compatible with that analyzer. They
    are not installed files and were not observed running.

"verbatim" means byte-identical to the source. "edited" means changed after extraction; the change is described below.

| File | wanctl source | Commit | Source sha256 | Status |
|---|---|---|---|---|
| `LICENSE` | `LICENSE` | 7677720f | c23aa671e740 | verbatim |
| `deploy/scripts/cake-metrics-exporter` | same | 7677720f | cd1be851e7e9 | verbatim |
| `deploy/scripts/cake-autorate-state-bridge` | `deploy/scripts/cake-autorate-spectrum-state-bridge` | 7677720f | 86f52be431f0 | edited (A) |
| `scripts/wanctl-bpctl-watchdog-petter` | same | 7677720f | f0423eb77b93 | verbatim |
| `scripts/wanctl-bpctl-watchdog-bypass` | same | 7677720f | cd9001ce2c6c | verbatim |
| `deploy/systemd/wanctl-bpctl-init` | same (not `scripts/wanctl-bpctl-init`) | 7677720f | c832651bd471 | verbatim |
| `scripts/silicom-bypass` | same | 7677720f | c44668aec688 | verbatim |
| `deploy/scripts/silicom-bypass.conf.example` | same | 7677720f | 7975b3cbb6ac | verbatim |
| `deploy/scripts/bpctl-watchdog-spectrum.env.example` | same | 7677720f | 59a9f18b57e8 | verbatim |
| `deploy/scripts/bpctl-watchdog-att.env.example` | same | 7677720f | e5a27d06cdee | verbatim |
| `deploy/systemd/cake-metrics-exporter.service` | same | 7677720f | e64368e0ab0e | edited (B) |
| `deploy/systemd/cake-autorate-state-bridge@.service` | `deploy/systemd/cake-autorate-spectrum-state-bridge.service` | 7677720f | 4f23cd56f98e | new, templated from source (C) |
| `deploy/scripts/bridge.env.example` | the two per-WAN bridge units | 7677720f | — | new (C) |
| `tests/test_install_contract.py` | — | — | — | new (H) |
| `deploy/systemd/bpctl-silicom.service` | same | 7677720f | b95150ebd349 | verbatim |
| `deploy/systemd/silicom-bypass-init.service` | same | 7677720f | a6a19d5d4b88 | verbatim |
| `deploy/systemd/silicom-bypass-watchdog@.service` | same | 7677720f | 9a94d62e2d28 | verbatim |
| `scripts/rrul-slot.sh` | same | 7677720f | 9d4d71d88596 | verbatim |
| `scripts/rrul_shadow_analyzer.py` | same | **13b1cf44** | a6134e7dff5f | verbatim (D) |
| `deploy/rrul-slot/env.example` | same | 7677720f | c38f71a81c8c | verbatim |
| `deploy/rrul-slot/wanctl-rrul-slot.service` | same | 7677720f | e1d340ec8ef8 | verbatim |
| `deploy/rrul-slot/wanctl-rrul-slot.timer` | same | **e4a6115d** | 47bc133d06b9 | verbatim (E) |
| `deploy/rrul-slot/wanctl-rrul-slot.timer.d/evening-sweeps.conf.example` | evening `OnCalendar=` lines of `deploy/rrul-slot/wanctl-rrul-slot.timer` | 7677720f | — | new (E) |
| `deploy/rrul-slot/wanctl-rrul-analyze.service` | same | 7677720f | f40f9143ef31 | verbatim |
| `deploy/rrul-slot/wanctl-rrul-analyze.timer` | same | 7677720f | 47df5359010c | verbatim |
| `scripts/capacity-sweep.sh` | same | 7677720f | 649b11fd7106 | verbatim |
| `deploy/capacity-sweep/env.example` | same | 7677720f | 89e0a6b0da95 | verbatim |
| `deploy/capacity-sweep/wanctl-capacity-sweep.service` | same | 7677720f | 2e4b7b167d54 | verbatim |
| `deploy/capacity-sweep/wanctl-capacity-sweep.timer` | same | 7677720f | 9a36b85137b1 | verbatim |
| `deploy/monitoring/grafana/network-cake.json` | same | 7677720f | 271ae93cad0b | verbatim |
| `docs/RRUL_SLOT.md` | same | **13b1cf44** | 4b3ec9fa8a44 | verbatim (D) |
| `docs/CAPACITY_SWEEP.md` | same | 7677720f | 1bb690f27998 | verbatim |
| `docs/SILICOM-BYPASS.md` | same | 7677720f | 6a2b68268213 | rewritten (F) |
| `docs/cake-on-mikrotik.md` | wanctl docs (cited inside) | 7677720f | — | new |
| `tests/test_cake_metrics_exporter.py` | same | 7677720f | 7de3619314c6 | edited (G) |
| `tests/test_cake_autorate_bridge_cake_stats.py` | same | 7677720f | 2a564754ee56 | edited (G) |
| `tests/test_cake_autorate_bridge_resources.py` | same | 7677720f | 274bf34e34bd | edited (G) |
| `tests/test_capacity_sweep.py` | same | 7677720f | f8f594528ee9 | verbatim |
| `tests/test_rrul_slot.py` | same | 7677720f | 68ad1a29707e | verbatim |
| `tests/test_rrul_slot_sweep.py` | same | 7677720f | b0b865103b35 | verbatim |
| `tests/test_rrul_shadow_analyzer.py` | same | **13b1cf44** | 0115d5614a8e | verbatim (D) |
| `tests/test_silicom_bypass_cli.py` | same | 7677720f | 71f5510030ae | edited (G) |
| `tests/__init__.py`, `tests/fixtures/cake-tc/{att,spectrum}.json` | same | 7677720f | 84a3178c97cd, 0ae0c7d31cdb, 75d286691943 | verbatim |
| `README.md`, `PROVENANCE.md`, `Makefile`, `pyproject.toml`, `.gitignore` | — | — | — | new |

## Edits

- **A.** wanctl shipped two bridge scripts, one per WAN, that differed only in one comment line. All per-WAN behavior
  already came from the environment. The Spectrum copy became the single generic bridge, with that comment line made
  WAN-neutral. Code is unchanged, including the built-in defaults.
- **B.** `CAKE_EXPORTER_BIND` now defaults to loopback, not a site address. `After=` no longer names the two per-WAN
  bridge units. A commented `CAKE_EXPORTER_WANS` hint was added.
- **C.** The two per-WAN bridge units, which differed only in `Environment=` values, became the template
  `cake-autorate-state-bridge@.service` plus an `EnvironmentFile` example with placeholders.
- **D.** The installed shadow analyzer was the 13b1cf44 version. wanctl main later added a phase-3 status record
  (`21c84d58`) used by a ceiling applier that is not part of this repository. The analyzer's doc and tests come from
  the same commit as the analyzer.
- **E.** The installed timer was the e4a6115d version, which has day slots only. The installed host also had a local
  timer drop-in, not reproduced here. wanctl main later added three evening `OnCalendar=` lines to the file. Add
  `OnCalendar=` lines, or a drop-in, for any sweep slots you use, and keep them equal to `RRUL_SLOT_SWEEP_SLOTS`.
- **F.** Rewritten as a short public reference. Site runbooks, host and pair identities, MAC addresses and
  deployment-specific procedures were left out. The measured conclusions are kept.
- **G.** Tests were ported to this layout. Assertions about wanctl's `deploy.sh`, rollback script, soak monitor,
  failure-injection harness and wanctl-only docs were removed. The bridge tests run the single generic bridge under
  both WAN configurations. The exporter-unit assertion follows edit B. The bridge durable-storage contract is checked
  against `README.md` and the env example.

- **H.** A new offline test checks two things. First, the bridge writes its state file mode 0600 and chowns it to the
  configured `WANCTL_STATE_UID`/`GID` before the atomic replace (with `os.chown` mocked). Second, the README prepares
  the exporter account before the first unit starts.

## Limitations of the extraction

- **Watchdog coverage is template-only.** The `silicom-bypass-watchdog@.service` template matches the installed
  template. One running watchdog instance used its own instance-specific unit file instead, and that file was not
  read or reproduced, so this repository does not represent its exact behavior.
- **The effective live rrul-slot schedule is not reproduced.** The installed timer had a local drop-in whose contents
  were not read. The evening drop-in example here is built from wanctl main, not from that file.
- **The capacity sweep is repository-only.** The expected script and unit paths were absent on the checked development
  host; installation elsewhere was not checked. Its script and units are the wanctl main versions, not observed
  installed bytes.
- **The Grafana dashboard's deployed identity is unverified.** The JSON is the wanctl main version; no deployed copy
  was compared.
- **Unit and env examples are templates.** The installed per-site units and env files contain site addresses and were
  not copied. Matching hashes cover the installed scripts and the generic unit files listed above, not the site
  configuration.

## Not included

- `wanctl-sweep-cap`, the shaper-side cap helper that rrul-slot's sweep mode calls. It was authored and installed
  separately, not part of wanctl.
- The retired single-purpose `silicom-bypass-watchdog-cake-autorate-att.service`, which is superseded by the
  `silicom-bypass-watchdog@` template.
- `scripts/wanctl-bpctl-dkms-install`, the wanctl `deploy.sh` wiring, the `silicom-test` harness and wanctl's
  controller code.
