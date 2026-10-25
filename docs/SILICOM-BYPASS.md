# Silicom bypass NIC: init, CLI and per-WAN fail-open watchdog

These tools drive a Silicom internal-bypass NIC (tested on a `PE2G4BPI35A-SD`) that carries an inline Linux CAKE
shaper bridge in each WAN pair. They need the out-of-tree `bpctl_mod` kernel module and `bpctl_util`, from the
public `bpctl-silicom` source (<https://github.com/ddos-mitigator/bpctl-silicom>; it is not known to be an official
Silicom upstream). Default paths are `/opt/bpctl-silicom/bpctl_util` and `/opt/bpctl-silicom/bpctl_mod.ko`.

**Every mutating command here can drop a WAN.** Run them only in a planned window. Nothing in this repository enables
or starts a unit.

## Pieces

| File | Installed as | Role |
|---|---|---|
| `deploy/systemd/wanctl-bpctl-init` | `/usr/local/sbin/wanctl-bpctl-init` | Loads `bpctl_mod`, recreates `/dev/bpctl0` from the registered major and checks `bpctl_util info`. **Read [Init script behavior](#init-script-behavior) first:** it can run `dkms` and `apt-get` as root |
| `deploy/systemd/bpctl-silicom.service` | `/etc/systemd/system/` | Oneshot that runs the init at boot. The extracted `Before=` names the original WAN units; edit it for yours |
| `scripts/silicom-bypass` | `/usr/local/sbin/silicom-bypass` | Operator CLI (below) |
| `deploy/scripts/silicom-bypass.conf.example` | `/etc/silicom-bypass.conf` | `PAIRS="<pair1> <pair2>"`: the control interface of each bypass pair |
| `deploy/systemd/silicom-bypass-init.service` | `/etc/systemd/system/` | Oneshot `silicom-bypass baseline` at boot. It must be enabled to take part in boot |
| `scripts/wanctl-bpctl-watchdog-petter` | `/usr/local/sbin/` | Arms the card watchdog and resets it every `HEARTBEAT_SECONDS` while `WANCTL_UNIT` is active. Sets bypass when the unit stops, and restores inline when it returns |
| `scripts/wanctl-bpctl-watchdog-bypass` | `/usr/local/sbin/` | Watchdog unit `ExecStop`: fail-open to bypass unless an operator-disarm sentinel exists |
| `deploy/systemd/silicom-bypass-watchdog@.service` | `/etc/systemd/system/` | Per-WAN watchdog. It reads `/etc/wanctl/bpctl-watchdog/%i.env` |
| `deploy/scripts/bpctl-watchdog-*.env.example` | `/etc/wanctl/bpctl-watchdog/<wan>.env` | `IFACE=<pair>` and `WANCTL_UNIT=<controller unit>`, for example `cake-autorate-<wan>.service` |

## Init script behavior

`wanctl-bpctl-init` is carried over byte for byte from the running deployment. It assumes a Debian-family host
(`dpkg`, `apt-get`, `/usr/sbin/dkms`). When `bpctl_mod` is not already loaded, it tries these steps in order:

1. `modprobe bpctl_mod`. On success it carries on to the device checks below.
2. `dkms autoinstall`, then `modprobe`. If that works, the script **exits 0 at once**, skipping the device-node and
   `bpctl_util info` checks.
3. If the package `linux-headers-$(uname -r)` is not installed: `apt-get -y -qq install linux-headers-$(uname -r)`,
   then `dkms autoinstall` and `modprobe`. On success it **exits 0 at once**, again without the checks. This step
   needs a working package source and network access at boot.
4. Last resort: `insmod` of the prebuilt `MODULE` (default `/opt/bpctl-silicom/bpctl_mod.ko`), which is likely to
   fail on a newer kernel.

After steps 1 and 4, or when the module was already loaded, it waits up to about 5 s for `bpctl` in `/proc/devices`.
It then recreates `/dev/bpctl0` (root:root, 0600) with the registered major and runs `bpctl_util info`. Each of those
checks failing fails the unit. If you don't want a boot-time package install, build the module with DKMS ahead of time
and verify the device yourself after an early-exit boot.

## CLI

```text
silicom-bypass status [pair|all]                        read-only, never cached
silicom-bypass on <pair> --yes [--both-wan-confirm]     powered bypass (drops the Linux path)
silicom-bypass off <pair>                               restore NIC path; idempotent
silicom-bypass disc <pair> --yes [--both-wan-confirm]   disconnect mode
silicom-bypass conn <pair>                              restore from disconnect; idempotent
silicom-bypass mark <label>                             journal + marks-log note, no card change
silicom-bypass baseline                                 apply and read back the boot policy on every pair
silicom-bypass arm <pair> [timeout_ms] --yes            enable that pair's fail-open watchdog
silicom-bypass disarm <pair>                            sentinel-clean stop, restore inline
```

Exit codes: 0 ok or no-op, 1 runtime refusal or read-back failure, 2 usage. `--both-wan-confirm` is required when the
other pair is already out of NIC mode.

`baseline` waits until each pair reports bypass capability. It then asserts `dis_bypass off`, `bypass_pwoff on`,
`bypass_pwup off`, `disc_pwup off` and `std_nic off`, skipping writes that already read correctly.

**Portability limit.** `arm`/`disarm` map pair names to watchdog instances in `pair_to_wd_instance()`. The extracted
code knows exactly two names, from the deployment it came from: `att-modem → att` and `spec-modem → spectrum`. Any
other pair name exits 2 until you add it there. `PAIRS` also defaults to those two names when no config is present.

## Watchdog rule (W-INV)

Stop, disable, restart or mask a fail-open watchdog only with `silicom-bypass disarm <pair>`. A raw
`systemctl stop|disable|restart|mask` runs the fail-open `ExecStop` without the disarm sentinel and puts the pair into
bypass. The petter reads `WANCTL_UNIT` once at start, so editing the env file does not re-point a running petter.
Disarm, edit, then arm again.

A normal host shutdown stops every armed watchdog, and with no sentinel present each one fails open. That is
intended: with the host down, raw ISP passthrough keeps the link up. The sentinel directory is tmpfs, so it is empty
after boot.

## What the card does and does not do (measured on one card, 2026-04-28)

- **Worked:** powered live bypass. Relays switch, the router side keeps carrier and the pair restores cleanly. The
  per-WAN watchdog also worked: stopping one WAN's controller bypassed only that pair, restarting it restored inline,
  and a warm host reboot passed traffic through bypass without a continuous ping dropping.
- **Did not work:** unpowered fail-open. With the host powered off, the WAN died, even when the pair was already in
  bypass before power was cut. The card reports zero PCIe AUX current, and its relays behaved as monostable. This
  card family targets software-failure bypass in a powered appliance, not chassis power loss. For power-loss
  passthrough use an external passive bypass switch, or a UPS on the host plus battery on the modem.
- The 5000 ms default watchdog timeout is rounded by the card to a 6400 ms hardware step, so don't promise exact
  expiry.
- A VM reboot is not a power-off test: the PCIe card stays powered.

The automated tests in `tests/test_silicom_bypass_cli.py` exercise the CLI, petter and bypass scripts against a fake
`bpctl_util` and a fake `systemctl`. They prove software behavior only, not relay timing.
