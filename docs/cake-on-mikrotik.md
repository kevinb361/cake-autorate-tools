# CAKE on MikroTik RouterOS: what we learned

This is a reference, not a controller. It records what the retired wanctl project learned while shaping two home WANs:
a DOCSIS cable link of roughly 1 Gbit down and 40 Mbit up, and a VDSL2 link of roughly 100 Mbit. It started with CAKE
queues on a MikroTik router driven over the REST API, and ended with CAKE on a Linux inline bridge driven by
[cake-autorate](https://github.com/lynxthecat/cake-autorate). The plan speeds above are approximate; the sources quote
several slightly different figures.

The wanctl code is archived for reference at `<wanctl-archive-url>`, commit `7677720f1b123512b6a59ec6f271338c851064cf`.
Its docs that this guide draws on are `docs/CABLE_TUNING.md`, `docs/CALIBRATION.md`, `docs/CONFIGURATION.md`,
`docs/GETTING-STARTED.md`, `docs/QOS_CLASSIFICATION_CONTRACT.md`, `docs/ARCHITECTURE.md` and
`docs/archive/TRANSPORT_COMPARISON.md`. Paths below refer to that commit.

**Read the limits first.**

- Almost every CAKE parameter number below (rtt, overhead, ack-filter, ceilings) was measured on the Linux shaper,
  not on RouterOS.
- The RouterOS-path measurements are a 2026-01-08 REST vs SSH transport test and the 2026-04-02 REST-era controller
  A/B tests.
- No RouterOS CAKE queue recipe in this guide was tested end to end as written.

## 1. RouterOS CAKE queue setup

wanctl never created queues. It expected them to exist already (`GETTING-STARTED.md`: RouterOS 7.x, "CAKE queues
already configured on the router"). What it relied on:

- **One CAKE queue type per WAN and direction.** The controller's batched write re-asserts the type on every change:
  `/queue tree set [find name="<download-queue>"] queue=cake-down-<wan> max-limit=<bps>` and the same for
  `cake-up-<wan>` (`src/wanctl/routeros_interface.py`).
- **One queue-tree entry per WAN and direction**, with `max-limit` as the single knob the controller moves. Values
  are in bits per second.
- **Queue-type parameters audited by `wanctl-check-cake`**, by their RouterOS REST field names
  (`src/wanctl/check_cake.py`):
  - link-independent: `cake-flowmode=triple-isolate`, `cake-diffserv=diffserv4`, `cake-nat=yes` (NAT on the router
    itself) and `cake-ack-filter=filter`, RouterOS's name for "on";
  - direction-dependent: `cake-wash=yes` on upload (CAKE classifies before washing, so diffserv4 still works) and
    `cake-wash=no` on download, so markings survive to LAN and Wi-Fi WMM;
  - link-dependent: `cake-overhead` and `cake-rtt` must match the link. The tool treats a mismatch as an error.
- **FastTrack off.** The classification contract says FastTrack "must remain disabled or be mechanically proven not
  to bypass classification" (`QOS_CLASSIFICATION_CONTRACT.md`).
- **REST enabled over HTTPS.** RouterOS ships a self-signed certificate. Either trust it explicitly on a trusted LAN or
  install the router's CA (`CONFIG_SCHEMA.md`). REST needs a password user; keep the password in a root-only
  `EnvironmentFile`, never in the repo or the YAML.

A sketch of that shape. It follows the field names above, but **this exact command set was not tested as written**.
Check it against MikroTik's CAKE documentation for your RouterOS version:

```routeros
/queue type
add name=cake-down-<wan> kind=cake cake-diffserv=diffserv4 cake-flowmode=triple-isolate cake-nat=yes \
    cake-wash=no cake-rtt=<rtt> cake-overhead=<bytes>
add name=cake-up-<wan> kind=cake cake-diffserv=diffserv4 cake-flowmode=triple-isolate cake-nat=yes \
    cake-wash=yes cake-ack-filter=filter cake-rtt=<rtt> cake-overhead=<bytes>
/queue tree
add name=<download-queue> parent=<lan-side-parent> queue=cake-down-<wan> max-limit=<initial-bps>
add name=<upload-queue> parent=<wan-interface-or-global> queue=cake-up-<wan> max-limit=<initial-bps>
```

The older snippets in wanctl's `docs/archive/` (QUICKSTART, EF_QUEUE_PROTECTION) are historical. One of them parents
both directions on the same interface. Pick the parents deliberately and confirm direction under load, as in section 4.

Two placement facts carried over from the Linux side, where they were measured:

- An `ingress`-style download CAKE disturbed the return-ACK path and collapsed upload tests on the cable link
  (2026-04-28, 2026-06-05).
- `nat` only helps where NAT happens on the same box (`QOS_CLASSIFICATION_CONTRACT.md`).

## 2. Why static limits fail on variable links

- **Idle jitter is not congestion.** DOCSIS adds about 5-15 ms of RTT jitter even on an idle link, from CMTS
  scheduling. DSL and fiber are near zero (`CABLE_TUNING.md`). A controller that reads that jitter as congestion
  oscillates.
- **Capacity moves with time of day.** A day-versus-night ceiling sweep on the cable link (2026-04-04/05, flent RRUL,
  10 runs per setting) found night medians within about 1.5 ms across all ceilings, while daytime was 10-18 ms worse
  everywhere. Variation was "dominated by DOCSIS node congestion (time-of-day), not by CAKE configuration". In 2026-10,
  at a fixed 780 Mbit ceiling, daytime loaded p99 was 50-65 ms. Evening runs delivered under 600 Mbit with p99 of
  150-230 ms, so the ceiling was not what was limiting them.
- **Once the ISP's buffer fills, CAKE can't help.** On the 40 Mbit upload plan, a 38 Mbit ceiling gave a 173 ms RRUL
  median, 35 gave 89 ms and 32 gave 47-95 ms (`CABLE_TUNING.md`, about 2026-04-03). The rule of thumb that came out of
  it was about 80 % of the plan. In the same work, a fixed 32 Mbit upload with no rate management gave a 126 ms median,
  against 47 ms with the controller active.
- **But cutting lower is not a cure.** In 2026-06, fixed download caps from 425 down to 150 Mbit did not make loaded
  latency acceptable on the cable link, and throughput collapsed. At 150 Mbit the cable link got 69 Mbit/s, with a
  worst-case p99 of 1.8 s. Path tests showed the added delay sat outside the local CAKE queue: LAN pings stayed
  sub-millisecond, and the local backlog was empty, while every internet target spiked together.

Static limits therefore lose both ways. Set high, the ISP-side queue fills at busy times. Set low enough for the worst
hour, you give away most of the link the rest of the day, and even that does not reliably fix the worst hour.

## 3. Driving `max-limit` from an external controller over REST

What wanctl actually did (`src/wanctl/routeros_rest.py`, `wan_controller.py`, `router_client.py`):

- Look up the queue id once with `GET /rest/queue/tree?name=<queue>`, and cache it.
- Set the rate with `PATCH /rest/queue/tree/<id>` and a body of `{"max-limit": "<bps>"}`. The controller path also
  sends `"queue": "<type>"`. **Every value in a PATCH body must be a string**, or RouterOS rejects it.
- Queue types have their own endpoint: `GET /rest/queue/type?name=<type>`, then `PATCH /rest/queue/type/<id>`.
- **Write only on change.** If neither rate changed since the last successful write, skip the router call entirely.
  On top of that, a RouterOS limiter allowed at most 5 rate changes per 10 s. The code says this is to protect the
  router's flash, but neither the write-wear figures in code comments nor a changelog's "99.7 % fewer writes" came with
  measurements. Treat change-only writes as cheap insurance, not as a measured requirement.
- **Fail over and come back.** At most two REST attempts per write, each with a 5 s timeout. Then switch to SSH (the
  equivalent `/queue/tree/set [find name="<queue>"] max-limit=<bps>`), and re-probe REST after 30 s, backing off ×2 to
  at most 300 s. If the router is unreachable, keep the wanted rate queued rather than dropping it.
- **Decide on RTT delta, not absolute RTT.** Freeze the baseline under load, cut immediately, and raise only after
  sustained healthy cycles. The controller polled every 50 ms.

Transport speed matters, because it is part of the control loop:

- **2026-01-08 test** (from a container, with 8 parallel upload streams for 3 minutes): REST took about 50 ms per
  command and SSH about 150-200 ms. REST peaked at 194 ms RTT against 404 ms for SSH, with no hard-congestion cycles
  against 5, and held download at 940 Mbit, while SSH fell to 417 Mbit (`docs/archive/TRANSPORT_COMPARISON.md`).
  REST is the better RouterOS transport.
- **Other figures.** `CABLE_TUNING.md` also quotes about 15-30 ms for REST, but no test backs that figure. A Linux
  `tc` change takes about 0.1 ms. Controller thresholds tuned on one transport did not carry over to the other.

## 4. What worked and what didn't

| Result | When | Where | Outcome |
|---|---|---|---|
| REST instead of SSH for rate writes | 2026-01-08 | RouterOS | worked (section 3) |
| Firmer YELLOW decay (8 % per cycle, not 3 %) and slower recovery for cable | 2026-04-02, 5-min RRUL A/B tests | RouterOS path, REST | worked: YELLOW decay factor 0.92 vs 0.97 cut ICMP p99 from 235 ms to 90.7 ms at equal throughput; 5 green cycles vs 3 cut upload p99 from 264 ms to 117 ms and raised upload from 19.5 to 22.2 Mbit |
| Threshold autotuning on cable | 2026-04 | — | didn't work: self-tightening spiral; exclude thresholds from autotuning on cable |
| CAKE `rtt` sweep 25-100 ms | 2026-04-02 | Linux | 40 ms best in that sweep (p99 113 ms vs 135-184 ms). Later configs used 25 ms and 100 ms, so treat rtt as link-specific and A/B it |
| Upload ceiling at about 80 % of plan | about 2026-04-03 | Linux | worked (section 2) |
| Lower static download caps | 2026-06-05/06 | Linux | didn't work: tail latency barely moved while throughput fell |
| Download `ingress` keyword | 2026-04-28, 2026-06-05 | Linux | didn't work: upload collapse |
| Upload ack-filter | 2026-04 to 2026-06 | Linux | inconsistent: required off at one point, later kept on for upload only |
| Offloads (GRO/GSO/TSO) off on the bridge ports | 2026-04-28 | Linux | worked: MTU-sized packets in CAKE, removed a severe ping-loss mode |
| HTB + fq_codel instead of CAKE | 2026-04-28, 2026-06-06 | Linux | not adopted: sometimes more throughput, inconsistent tail |
| CAKE on a bridge device itself | 2026-06-06 | Linux | didn't work: shaped nothing; put CAKE on the member ports' egress |
| cake-autorate vs the wanctl native controller | 2026-06-05 | Linux | VDSL2 link: equal within noise (84.4 vs 83.5/84.6 Mbit, p99 about 60 ms). Cable link: recorded as "materially better" user-visible results, with no paired numbers in the record |
| Silicom bypass NIC for fail-open | 2026-04-28 | Linux | powered watchdog bypass worked; power-loss fail-open did not (see [SILICOM-BYPASS.md](SILICOM-BYPASS.md)) |

A practical lesson from 2026-04-28: after recabling, confirm direction with `ip -s link` and `tc -s qdisc` under load.
Reversed port roles once put the 32 Mbit upload shaper on the download path, and downloads crawled at 10-17 Mbit.

## 5. Why the setup moved to a Linux shaper with cake-autorate

1. **RouterOS queues to a Linux inline bridge.** Rate changes became local `tc` calls instead of HTTP round trips.
   That made the feedback loop much faster and changed which controller settings were best. The design split the
   edge in two:
   - RouterOS keeps classification (DSCP), NAT and routing, with FastTrack off;
   - the bridge owns CAKE, wash, tins and rates.

   The cost is that a shaper sitting after NAT can't give true per-LAN-host fairness (`QOS_CLASSIFICATION_CONTRACT.md`).
   The record contains no same-settings A/B of RouterOS CAKE against Linux CAKE. The move was made for control-loop
   speed and flexibility, not because of a measured RouterOS deficit.
2. **wanctl's controller to upstream cake-autorate** (2026-06). The direction was to use cake-autorate where evidence
   showed it equal or better. It was equal on the VDSL2 link and judged better on the cable link, and it is built for
   variable-rate links. Only one controller may write CAKE rates at a time. wanctl stayed on only as the state bridge,
   metrics and health layer, which is what this repository now contains.
3. **Retiring wanctl** (2026-10). Nothing live used its controller any more. The project's planning record gives a
   baseline for the seven days ending 2026-10-25, over all samples, loaded or not: p50 0.2 ms, p90 4.4 ms, p95 9.1 ms
   and p99 20 ms, with 91 % of samples at or under 5 ms and a worst evening hour p95 of 28-35 ms. The record does not
   name the exact metric. Its context ("p99 latency rise about 20 ms") points to added latency (RTT increase), not
   absolute internet RTT. It was not re-measured for this guide. The working goal under RRUL load is a median added latency of 5 ms or less, p95
   of 15 ms or less, and no evening blow-ups. On DOCSIS, upstream request-grant jitter makes a 5 ms p95 under
   sustained load unlikely without shaping lower.

If you stay on RouterOS:

- use REST and write only on change;
- size the upload ceiling to about 80 % of plan;
- treat CAKE `rtt` and overhead as per-link values you A/B test;
- expect the evening ISP-side queue to be the limit that no static number fixes.
