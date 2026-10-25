# cake-autorate-tools

These are small helpers and measurement tools that run around
[cake-autorate](https://github.com/lynxthecat/cake-autorate) on a Linux CAKE shaper. They are extracted from
wanctl (archived at `<wanctl-archive-url>`), a retired adaptive CAKE controller for MikroTik RouterOS. Once
cake-autorate took over live rate control, these were the pieces still in use or kept for measurement. The capacity
sweep and the dashboard are taken from the repository rather than an installed copy. See the limitations in
[PROVENANCE.md](PROVENANCE.md#limitations-of-the-extraction).

None of them shapes traffic. cake-autorate does that. These tools:

| Tool | What it does | Runs on |
|---|---|---|
| `deploy/scripts/cake-autorate-state-bridge` | Tails cake-autorate's log and writes per-WAN state JSON, a SQLite metrics DB and a `/health` endpoint | shaper (root) |
| `deploy/scripts/cake-metrics-exporter` | Read-only Prometheus exporter over the bridge's state JSON | shaper (unprivileged) |
| `scripts/silicom-bypass`, `scripts/wanctl-bpctl-watchdog-*`, `deploy/systemd/wanctl-bpctl-init` | Silicom bypass NIC init, operator CLI and per-WAN fail-open watchdog. See [docs/SILICOM-BYPASS.md](docs/SILICOM-BYPASS.md) | shaper (root) |
| `scripts/rrul-slot.sh` | One flent RRUL measurement per time slot, or an evening cap sweep. See [docs/RRUL_SLOT.md](docs/RRUL_SLOT.md) | a LAN measurement host (user) |
| `scripts/rrul_shadow_analyzer.py` | Turns rrul-slot rows into a daily per-hour *shadow* cap recommendation. It applies nothing | measurement host (user) |
| `scripts/capacity-sweep.sh` | Paced iperf3 + fping download capacity sweep. See [docs/CAPACITY_SWEEP.md](docs/CAPACITY_SWEEP.md) | measurement host (user) |
| `deploy/monitoring/grafana/network-cake.json` | Grafana dashboard for the exporter's metrics | Grafana |

For background on CAKE with RouterOS, and why this setup moved to a Linux shaper, see
[docs/cake-on-mikrotik.md](docs/cake-on-mikrotik.md).

Installed command and unit names keep their `wanctl-` prefixes, so existing installs and their timers keep working.
Renaming them is a separate, deliberate step.

## Requirements

- **Shaper:** Linux with CAKE (`sch_cake`), `tc`, Python 3.11+ (stdlib only) and cake-autorate. The Silicom tools
  additionally need the `bpctl_mod` kernel module and `bpctl_util`; see the Silicom doc.
- **Measurement host:** bash, GNU awk, `jq`, `flock`/`setsid` (util-linux), procps `pgrep`, and coreutils `timeout`.
  rrul-slot also needs `flent` (with `netperf`), `fping` and `irtt`. The capacity sweep needs `iperf3` and `fping`. Both
  need a read-only Prometheus query command (`prom-ro` or the configured `*_PROM_CMD`) and a netperf/iperf3 endpoint you
  control.
- **Sweep mode** of rrul-slot needs a shaper-side helper, `wanctl-sweep-cap`, which this repository does **not**
  ship. It freezes the controller, holds a CAKE download cap and restores it under a dead-man timer; its call protocol is documented in
  [docs/RRUL_SLOT.md](docs/RRUL_SLOT.md#sweep-mode). Without it, sweep slots fail before any load. `auto` mode selects
  sweep when a run starts within 10 minutes after one of `RRUL_SLOT_SWEEP_SLOTS`, which defaults to
  `19:35 21:05 22:35` Central when unset. Without the helper, set `RRUL_SLOT_SWEEP_SLOTS=` (empty) in the env file.

## Install

Installing the files changes nothing that is running. The `systemctl enable --now` lines are the manual activation
step. Every unit runs real traffic or controls live interfaces, so run those lines only after you have edited the
units and env files for your site.

### Account and directories (before starting any unit)

The bridge runs as root. It writes each `<wan>_state.json` as a mode-0600 file and chowns it to `WANCTL_STATE_UID`
and `WANCTL_STATE_GID`, which default to 988, before the atomic replace. The exporter reads those files as the
unprivileged `wanctl` account. Both sides must therefore name the same account, or the exporter reports
`cake_state_up 0`.

```sh
sudo useradd --system --no-create-home --shell /usr/sbin/nologin wanctl   # or reuse an existing account
sudo install -d -m 0755 /var/lib/wanctl
id -u wanctl; id -g wanctl   # put these into WANCTL_STATE_UID / WANCTL_STATE_GID in every bridge env file
```

If you run the exporter as another account, change its `User=`/`Group=` and use that account's IDs instead. Setting
`WANCTL_STATE_CHOWN=0` leaves the state files root-owned and mode 0600, so the exporter can't read them.

### State bridge (one instance per WAN)

```sh
sudo install -D -m 0755 deploy/scripts/cake-autorate-state-bridge /usr/local/sbin/cake-autorate-state-bridge
sudo install -D -m 0644 deploy/systemd/cake-autorate-state-bridge@.service /etc/systemd/system/
sudo install -D -m 0600 deploy/scripts/bridge.env.example /etc/cake-autorate-tools/bridge-<wan>.env   # edit it
sudo systemctl daemon-reload
sudo systemctl enable --now cake-autorate-state-bridge@<wan>.service
curl -s http://127.0.0.1:<health-port>/health
```

The bridge reads its whole configuration from the environment. Its built-in interface defaults belong to the
deployment it was extracted from, so set `WANCTL_EXTERNAL_DL_IF` and `WANCTL_EXTERNAL_UL_IF` explicitly. The per-WAN
metrics databases must remain regular files under `/var/lib/wanctl`. Symlinking them into `/run/wanctl` is
unsupported.

Rollback: `systemctl disable --now cake-autorate-state-bridge@<wan>.service`, then remove the unit, the env file and
the script.

### Metrics exporter

```sh
sudo install -D -m 0755 deploy/scripts/cake-metrics-exporter /usr/local/sbin/cake-metrics-exporter
sudo install -D -m 0644 deploy/systemd/cake-metrics-exporter.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now cake-metrics-exporter.service
curl -s http://127.0.0.1:9103/metrics | head
```

The exporter runs as the account prepared above (`User=wanctl`). It binds to loopback by default.
To scrape it remotely, set `CAKE_EXPORTER_BIND` in a drop-in to a firewall-restricted address, and set
`CAKE_EXPORTER_WANS` to your WAN names. Import `deploy/monitoring/grafana/network-cake.json` into Grafana and point it
at your Prometheus data source.

### Silicom bypass NIC

See [docs/SILICOM-BYPASS.md](docs/SILICOM-BYPASS.md). Install the scripts to `/usr/local/sbin`, the units to
`/etc/systemd/system`, `silicom-bypass.conf.example` to `/etc/silicom-bypass.conf`, and one
`/etc/wanctl/bpctl-watchdog/<wan>.env` per watched pair. Then edit the `Before=` lines and the pair-to-instance map
for your interfaces.

### rrul-slot, shadow analyzer, capacity sweep (measurement host, as a user)

Follow the install sections of [docs/RRUL_SLOT.md](docs/RRUL_SLOT.md) and [docs/CAPACITY_SWEEP.md](docs/CAPACITY_SWEEP.md).
In short:

```sh
install -D -m 0755 scripts/rrul-slot.sh ~/.local/bin/wanctl-rrul-slot
install -D -m 0755 scripts/rrul_shadow_analyzer.py ~/.local/bin/wanctl-rrul-analyze
install -D -m 0755 scripts/capacity-sweep.sh ~/.local/bin/wanctl-capacity-sweep
install -D -m 0600 deploy/rrul-slot/env.example ~/.config/wanctl-rrul/env          # edit real values
install -D -m 0600 deploy/capacity-sweep/env.example ~/.config/wanctl-sweep/env    # edit real values
```

`deploy/rrul-slot/wanctl-rrul-slot.timer` carries the four day slots. The evening sweep slots that
[docs/RRUL_SLOT.md](docs/RRUL_SLOT.md) describes are an optional drop-in,
`deploy/rrul-slot/wanctl-rrul-slot.timer.d/evening-sweeps.conf.example`; install it only together with the sweep
helper. The `--user` units under `deploy/rrul-slot/` and `deploy/capacity-sweep/` are proposals. Read each doc's schedule
section before you enable a timer. Only one measurement tool may generate load at a time: each one refuses to start
while another load tool runs, and treats a failed check (for example a missing `pgrep`) as a reason not to start.

## Development

```sh
make test     # pytest; every external tool is a fake, no network or service access
make lint     # ruff and shellcheck
make ci       # lint + test
```

The tests need the tools listed for the measurement host (bash, GNU awk, jq, flock, setsid, pgrep, timeout) and
Python 3.11+ with pytest. With pytest-xdist installed, `make test` runs in parallel with `--dist=loadfile`. That keeps
all tests of one module on the same worker, which the capacity-sweep tests need because they must not run
concurrently with each other. It does not isolate the host's process table between workers.

## License and provenance

GPL-2.0 (see [LICENSE](LICENSE)). The code derives from wanctl, which is GPL-2.0. [PROVENANCE.md](PROVENANCE.md)
lists the wanctl commit and the source checksum for each file, and says whether the file was copied verbatim or
edited.
