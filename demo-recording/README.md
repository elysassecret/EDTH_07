# PHAROS 3-Minute Automated Pitch Demo Recording

Automated, deterministic recording pipeline using Playwright and FFmpeg to produce a silent, high-definition 1920×1080 30fps MP4 video (`pharos-pitch.mp4`) for the 3-minute live startup pitch.

The video aligns second-by-second with the 4-speaker pitch delivery (Franko, Sime, Javier, Alex, Franko).

---

## 1. Quick Start

Run the complete pipeline with one command from either `web/` or the repository root:

```bash
# From repository root
npm --prefix web run record:pitch

# Or directly with Node:
node demo-recording/record.mjs
```

The script will:
1. Validate timeline consistency (180.00s total duration).
2. Build the latest production bundle (`web/dist`).
3. Start the PHAROS simulation server in deterministic demo mode (`server/demo.toml`, seed 1).
4. Launch Chromium in 1920×1080 headless mode.
5. Navigate to `http://127.0.0.1:8878/?pitch=true`.
6. Record all 5 pitch scenes over 180 seconds with real-time camera movements, telemetry, failure injections, and overlays.
7. Encode the final video with FFmpeg to 1080p H.264 at exactly 180.00 seconds.
8. Extract 12 keyframe review screenshots into `demo-recording/output/`.
9. Validate the resulting file with FFprobe.

The output MP4 is saved to:
```
demo-recording/output/pharos-pitch.mp4
```

---

## 2. Storyboard & Scene Breakdown

| Timestamp | Speaker | Topic | Visuals on Screen |
|---|---|---|---|
| **00:00–00:12** | **FRANKO** | Gulf of Finland Cable Cut | Dark nautical map reconstruction showing 90 km dragged anchor trail cutting 5 undersea cables (EstLink 1/2, Balticconnector, EE-FI-1/2). |
| **00:12–00:23** | **FRANKO** | PHAROS Swarm Intro | Seamless camera flight into live Great Belt dashboard. 5 USVs in formation connected by cyan radio mesh lines. |
| **00:23–00:35** | **FRANKO** | Sensor Coverage & Batteries | Smooth camera zoom into patrol formation. Active sensor detection rings. Fleet panel displaying battery gauges. |
| **00:35–00:45** | **SIME** | The Battery Problem | Conventional patrol boats drain power in hours. Introduction to satellite-inspired drift keeping. |
| **00:45–00:55** | **SIME** | Drift Station-Keeping | Real ocean current vectors displayed (0.3 m/s SSE). USVs drift with tide; micro-thrust pulses on boundaries. "MOTORS OFF · SENSORS ON". |
| **00:55–01:02** | **SIME** | 10× Less Power | Energy telemetry card: 100% continuous cruise load vs 10% drift hotel load (`hotel_load_permille = 100`). Days at sea instead of hours. |
| **01:02–01:07** | **SIME** | Boat Failure ("Watch this") | USV 01 triggers low battery reserve (`battery_low`). Status turns red; returns to Korsør. Cable sector becomes open. |
| **01:07–01:12** | **SIME** | Autonomous Gap Coverage | Swarm autonomously redistributes: USV 04 reallocates to cover USV 01's sector. Patrol gap closed without human input. |
| **01:12–01:15** | **SIME** | 30 Tests Validation | Validation scorecard: "30 TESTS · 0 RESERVE VIOLATIONS" from `world/endurance.py`. |
| **01:15–01:30** | **JAVIER** | Transparent Shore Decision | Focus on Decision panel. Plain-language reason from `agent/auction.py`: "USV-04 assigned to Sector C · Reason: lowest available assignment cost [battery return]". |
| **01:30–01:42** | **JAVIER** | Relay Vessel Failure | USV 05 relay cut (`boat_off`). Radio mesh dynamically reconfigures: USV 03 automatically elected as replacement relay (`deputy takeover`). |
| **01:42–01:53** | **JAVIER** | Shore Link Cut & Reconnect | Shore link cut. Vessels continue autonomous patrol. Store-and-forward telemetry buffered on boats. Shore link restored & synchronized. |
| **01:53–01:58** | **JAVIER** | Zero Single Point of Failure | Pull back showing resilient distributed mesh. "No boss: how do four boats agree?" |
| **01:58–02:08** | **ALEX** | Slotted Distributed Auction | Cable task opens for bidding. Floating bid pills over USVs (`agent/auction.py`). |
| **02:08–02:18** | **ALEX** | Cost Formula & Consensus | Mathematical formulation: `TOTAL COST = ENERGY / TIME COST + COVERAGE RISK`. Bids propagate peer-to-peer to identical winner. |
| **02:18–02:25** | **ALEX** | Partition Tolerance | Communication graph splitting and reconvergence without state corruption. |
| **02:25–02:34** | **ALEX** | Hardware Architecture | Retrofit box (EUR 2,500–4,500): Raspberry Pi CM5 + Pixhawk 6X. ArduPilot MAVLink telemetry. "NO GPUs · NO NEW HULL". |
| **02:34–02:43** | **FRANKO** | Return to the Swarm | Wide panoramic view of stable Great Belt patrol after all simulated disruptions. |
| **02:43–02:55** | **FRANKO** | The Three Statements | Sequential statement cards over live swarm: 1) "DAYS AT SEA", 2) "ONE OPERATOR", 3) "A DETECTION BOX". |
| **02:55–03:00** | **FRANKO** | Grand Finale Brand Screen | Cinematic fade to deep maritime navy with glowing PHAROS insignia and tagline: "Autonomous Protection for Critical Maritime Infrastructure". |

---

## 3. How to Adjust Timings

All timestamps and scene boundaries are centralized in:
```
demo-recording/timeline.json
```
To adjust a speaker's duration (e.g. adding 3 seconds to Sime's scene), update the `start`, `end`, and `duration` fields in `timeline.json`. Ensure the sum of all durations equals 180 seconds.

---

## 4. Architecture & Design Principles

- **True PHAROS Integration**: The recording captures the live WebGL/MapLibre map, actual Great Belt cables, live deck.gl layers, real telemetry feed, and authentic auction reasons from `agent/auction.py`.
- **Zero Production Degradation**: Normal operation at `http://localhost:8765/` is untouched. The pitch presenter only mounts when `?pitch=true` is present.
- **Deterministic**: Seed 1 simulation (`server/demo.toml`), fixed coordinate transforms, and monotonic time synchronization ensure identical output every run.
- **Broadcast-Ready**: 1920×1080 30 FPS MP4 with H.264 video encoding, zero cursor clutter, and no debug windows.

---

## 5. Verification Commands

To verify the generated MP4 file properties:
```bash
ffprobe -v error -show_entries stream=width,height,r_frame_rate,codec_name:format=duration,size -of default=noprint_wrappers=1 demo-recording/output/pharos-pitch.mp4
```

Expected output:
```
codec_name=h264
width=1920
height=1080
r_frame_rate=30/1
duration=180.000000
```
