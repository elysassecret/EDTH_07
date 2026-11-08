import { useEffect, useRef, useState } from "react";
import { useStore } from "../store";

export interface PitchTimelineScene {
  id: string;
  speaker: string;
  start: number;
  end: number;
  duration: number;
  title: string;
}

export const PITCH_TIMELINE: PitchTimelineScene[] = [
  { id: "scene_1", speaker: "FRANKO", start: 0, end: 35, duration: 35, title: "The Gulf of Finland Incident & The Swarm" },
  { id: "scene_2", speaker: "SIME", start: 35, end: 75, duration: 40, title: "Batteries, Drift Station-Keeping & Failure" },
  { id: "scene_3", speaker: "JAVIER", start: 75, end: 118, duration: 43, title: "Autonomous Decision, Relay & Shore Loss" },
  { id: "scene_4", speaker: "ALEX", start: 118, end: 154, duration: 36, title: "The Distributed Auction & Hardware" },
  { id: "scene_5", speaker: "FRANKO", start: 154, end: 180, duration: 26, title: "The Future & Conclusion" },
];

export function PitchDirector() {
  const [t, setT] = useState(0);
  const [active, setActive] = useState(false);
  const startTimeRef = useRef<number | null>(null);
  const firedEventsRef = useRef<Set<string>>(new Set());

  const conn = useStore((s) => s.conn);
  const send = useStore((s) => s.send);

  // Master clock running monotonic timeline 0..180s
  useEffect(() => {
    let animId: number;

    const startTimer = () => {
      startTimeRef.current = performance.now();
      setActive(true);
      (window as unknown as { __pharos_pitch_ready?: boolean; __pharos_pitch_lead?: number }).__pharos_pitch_ready = true;
      (window as unknown as { __pharos_pitch_ready?: boolean; __pharos_pitch_lead?: number }).__pharos_pitch_lead = performance.now() / 1000;
    };

    // Wait until simulation is connected and map is ready
    const checkReady = setInterval(() => {
      const map = (window as unknown as { __pharos_map?: { isStyleLoaded: () => boolean } }).__pharos_map;
      if (conn === "live" && map && (!map.isStyleLoaded || map.isStyleLoaded())) {
        clearInterval(checkReady);
        startTimer();
      }
    }, 200);

    const tick = (now: number) => {
      if (startTimeRef.current !== null) {
        const elapsed = (now - startTimeRef.current) / 1000;
        setT(elapsed);
        (window as unknown as { __pharos_pitch_time?: number }).__pharos_pitch_time = elapsed;
      }
      animId = requestAnimationFrame(tick);
    };
    animId = requestAnimationFrame(tick);

    return () => {
      clearInterval(checkReady);
      cancelAnimationFrame(animId);
    };
  }, [conn]);

  // Orchestrate camera movements and simulation events at precise timestamps
  useEffect(() => {
    if (!active) return;
    const fired = firedEventsRef.current;
    const map = (window as unknown as {
      __pharos_map?: {
        flyTo: (opts: { center: [number, number]; zoom: number; duration?: number; essential?: boolean }) => void;
      };
    }).__pharos_map;

    const fireOnce = (id: string, fn: () => void) => {
      if (!fired.has(id)) {
        fired.add(id);
        fn();
      }
    };

    // T = 12s: Transition into Great Belt live dashboard
    if (t >= 12.0 && t < 13.0) {
      fireOnce("t_12_unpause", () => {
        send({ cmd: "pause", on: false });
        if (map) {
          map.flyTo({ center: [10.98, 55.35], zoom: 10.6, duration: 2500, essential: true });
        }
      });
    }

    // T = 23s: Smooth zoom into active patrol formation
    if (t >= 23.0 && t < 25.0) {
      fireOnce("t_23_zoom_fleet", () => {
        if (map) {
          map.flyTo({ center: [10.96, 55.42], zoom: 12.0, duration: 3500, essential: true });
        }
      });
    }

    // T = 45s: Scene 2 drift station-keeping camera follow
    if (t >= 45.0 && t < 47.0) {
      fireOnce("t_45_drift_view", () => {
        if (map) {
          map.flyTo({ center: [10.97, 55.39], zoom: 12.6, duration: 4000, essential: true });
        }
      });
    }

    // T = 63s: Scene 2 boat failure trigger ("Watch this")
    if (t >= 63.0 && t < 65.0) {
      fireOnce("t_63_fail_boat_01", () => {
        send({ cmd: "inject", kind: "battery_low", a: 1 });
        if (map) {
          map.flyTo({ center: [10.97, 55.37], zoom: 11.2, duration: 2500, essential: true });
        }
      });
    }

    // T = 90s: Scene 3 relay vessel failure (USV 05 offline)
    if (t >= 90.0 && t < 92.0) {
      fireOnce("t_90_relay_off", () => {
        send({ cmd: "inject", kind: "boat_off", a: 5 });
        if (map) {
          map.flyTo({ center: [11.02, 55.34], zoom: 11.6, duration: 2500, essential: true });
        }
      });
    }

    // T = 104s: Scene 3 shore link cut
    if (t >= 104.0 && t < 106.0) {
      fireOnce("t_104_link_cut", () => {
        send({ cmd: "inject", kind: "link_off", a: 4, b: "shore" });
      });
    }

    // T = 118s: Scene 4 auction visualization wide view
    if (t >= 118.0 && t < 120.0) {
      fireOnce("t_118_auction_view", () => {
        if (map) {
          map.flyTo({ center: [10.98, 55.36], zoom: 11.0, duration: 2500, essential: true });
        }
      });
    }

    // T = 154s: Scene 5 wide strategic corridor
    if (t >= 154.0 && t < 156.0) {
      fireOnce("t_154_closing_pan", () => {
        if (map) {
          map.flyTo({ center: [10.96, 55.36], zoom: 10.3, duration: 4000, essential: true });
        }
      });
    }
  }, [t, active, send]);

  return (
    <div
      id="pitch-director-root"
      style={{
        position: "fixed",
        inset: 0,
        pointerEvents: "none",
        zIndex: 999999,
        fontFamily: "'Inter', system-ui, sans-serif",
      }}
    >
      {/* 1. SCENE 1 (0:00 - 0:12): HISTORICAL GULF OF FINLAND INCIDENT RECONSTRUCTION */}
      {t < 12.2 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "#04090f",
            opacity: t > 11.2 ? Math.max(0, 1 - (t - 11.2)) : 1,
            transition: "opacity 0.6s ease-out",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "48px 64px",
            boxSizing: "border-box",
          }}
        >
          {/* Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div
                style={{
                  color: "#ef4444",
                  fontSize: 14,
                  fontWeight: 700,
                  letterSpacing: "0.15em",
                  textTransform: "uppercase",
                  marginBottom: 8,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444", display: "inline-block" }} />
                HISTORICAL EVENT RECONSTRUCTION · GULF OF FINLAND
              </div>
              <div style={{ color: "#ffffff", fontSize: 38, fontWeight: 800, letterSpacing: "-0.02em" }}>
                DECEMBER 2024: 90 KM DRAGGED ANCHOR
              </div>
            </div>
            <div
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                padding: "10px 20px",
                borderRadius: 8,
                color: "#fca5a5",
                fontSize: 18,
                fontWeight: 700,
              }}
            >
              5 UNDERSEA CABLES SEVERED
            </div>
          </div>

          {/* Center Graphic: Nautical Map Reconstruction of Gulf of Finland */}
          <div style={{ position: "relative", width: "100%", height: 620, margin: "20px 0" }}>
            <svg width="100%" height="100%" viewBox="0 0 1600 620" style={{ overflow: "visible" }}>
              {/* Background maritime grid lines */}
              <defs>
                <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
                  <path d="M 80 0 L 0 0 0 80" fill="none" stroke="rgba(56, 189, 248, 0.05)" strokeWidth="1" />
                </pattern>
                <linearGradient id="anchorGlow" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity="1" />
                </linearGradient>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />

              {/* Land outlines: Finland (North) */}
              <path
                d="M 50,40 Q 200,80 400,60 T 800,90 T 1200,70 T 1550,50 L 1550,0 L 50,0 Z"
                fill="#0f1f2e"
                stroke="#1e3a52"
                strokeWidth="2"
              />
              <text x="700" y="55" fill="#476f94" fontSize="16" fontWeight="700" letterSpacing="0.1em">FINLAND (HELSINKI WATERS)</text>

              {/* Land outlines: Estonia (South) */}
              <path
                d="M 50,560 Q 300,520 600,540 T 1000,510 T 1400,530 T 1550,570 L 1550,620 L 50,620 Z"
                fill="#0f1f2e"
                stroke="#1e3a52"
                strokeWidth="2"
              />
              <text x="680" y="590" fill="#476f94" fontSize="16" fontWeight="700" letterSpacing="0.1em">ESTONIA (TALLINN WATERS)</text>

              {/* Undersea cables crossing Gulf */}
              {/* Cable 1: EstLink 1 */}
              <line x1="450" y1="70" x2="430" y2="530" stroke="#f59e0b" strokeWidth="3" strokeDasharray="6 4" />
              <text x="455" y="160" fill="#f59e0b" fontSize="13" fontWeight="600">EstLink 1 (HVDC)</text>

              {/* Cable 2: Balticconnector */}
              <line x1="620" y1="85" x2="590" y2="535" stroke="#f59e0b" strokeWidth="3" strokeDasharray="6 4" />
              <text x="625" y="210" fill="#f59e0b" fontSize="13" fontWeight="600">Balticconnector</text>

              {/* Cable 3: EstLink 2 */}
              <line x1="820" y1="88" x2="790" y2="520" stroke="#f59e0b" strokeWidth="3" strokeDasharray="6 4" />
              <text x="825" y="270" fill="#f59e0b" fontSize="13" fontWeight="600">EstLink 2 (650 MW)</text>

              {/* Cable 4: EE-FI-1 Telecom */}
              <line x1="1020" y1="75" x2="990" y2="515" stroke="#f59e0b" strokeWidth="3" strokeDasharray="6 4" />
              <text x="1025" y="320" fill="#f59e0b" fontSize="13" fontWeight="600">EE-FI-1 Subsea Fibre</text>

              {/* Cable 5: EE-FI-2 Telecom */}
              <line x1="1200" y1="65" x2="1170" y2="525" stroke="#f59e0b" strokeWidth="3" strokeDasharray="6 4" />
              <text x="1205" y="370" fill="#f59e0b" fontSize="13" fontWeight="600">EE-FI-2 Telecom</text>

              {/* Anchor Dragging Path (Westward trajectory) */}
              <path
                d="M 1480,240 C 1300,260 1000,310 700,340 S 350,380 200,410"
                fill="none"
                stroke="url(#anchorGlow)"
                strokeWidth="5"
                strokeDasharray="8 4"
              />

              {/* Fracture impact marks on cables */}
              {[
                { x: 1190, y: 275 },
                { x: 1005, y: 308 },
                { x: 808, y: 330 },
                { x: 605, y: 350 },
                { x: 440, y: 382 },
              ].map((pt, i) => (
                <g key={i}>
                  <circle cx={pt.x} cy={pt.y} r="18" fill="rgba(239, 68, 68, 0.25)" stroke="#ef4444" strokeWidth="2" />
                  <text x={pt.x} y={pt.y + 5} fill="#ffffff" fontSize="16" fontWeight="900" textAnchor="middle">✕</text>
                  <text x={pt.x + 22} y={pt.y - 12} fill="#ef4444" fontSize="11" fontWeight="700">CUT #{5 - i}</text>
                </g>
              ))}

              {/* Tanker Icon along trajectory */}
              <g transform="translate(320, 395) rotate(-14)">
                <rect x="-24" y="-10" width="48" height="20" rx="4" fill="#ef4444" stroke="#ffffff" strokeWidth="2" />
                <polygon points="24,-10 36,0 24,10" fill="#ef4444" stroke="#ffffff" strokeWidth="2" />
                <text x="0" y="32" fill="#fca5a5" fontSize="12" fontWeight="700" textAnchor="middle">VESSEL DRAGGING ANCHOR (90 KM)</text>
              </g>
            </svg>
          </div>

          {/* Bottom Footer Note */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderTop: "1px solid rgba(255, 255, 255, 0.1)",
              paddingTop: 16,
              color: "#94a3b8",
              fontSize: 16,
            }}
          >
            <div>Hours of anchor dragging went undetected · Conventional patrols could not be everywhere</div>
            <div style={{ color: "#38bdf8", fontWeight: 700 }}>PHAROS SOLUTION INCOMING →</div>
          </div>
        </div>
      )}

      {/* 2. PERSISTENT UPPER-LEFT HUD BANNER (0:12 - 2:34) */}
      {t >= 12.0 && t < 154.0 && (
        <div
          style={{
            position: "absolute",
            top: 24,
            left: 24,
            background: "rgba(7, 18, 28, 0.88)",
            border: "1px solid rgba(56, 189, 248, 0.25)",
            backdropFilter: "blur(12px)",
            padding: "12px 24px",
            borderRadius: 10,
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div
            style={{
              width: 12,
              height: 12,
              borderRadius: "50%",
              background: "#00e5ff",
              boxShadow: "0 0 12px #00e5ff",
            }}
          />
          <div>
            <div style={{ color: "#ffffff", fontSize: 16, fontWeight: 800, letterSpacing: "-0.01em" }}>
              PHAROS · AUTONOMOUS USV SWARM
            </div>
            <div style={{ color: "#7dd3fc", fontSize: 13, fontWeight: 500 }}>
              {t < 35 && "5 Vessels · Distributed Radio Mesh · Single Hive Mind"}
              {t >= 35 && t < 75 && "Autonomous Station-Keeping & Drift Optimization"}
              {t >= 75 && t < 118 && "Distributed Consensus · Self-Healing Mesh Network"}
              {t >= 118 && t < 154 && "Slotted Local Auction · ArduPilot Integration"}
            </div>
          </div>
        </div>
      )}

      {/* 3. SCENE 2: DRIFT STATION-KEEPING BANNER (0:45 - 0:55) */}
      {t >= 45.0 && t < 55.0 && (
        <div
          style={{
            position: "absolute",
            top: 100,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(7, 24, 38, 0.92)",
            border: "1px solid #00e5ff",
            boxShadow: "0 0 24px rgba(0, 229, 255, 0.3)",
            padding: "16px 36px",
            borderRadius: 12,
            textAlign: "center",
            backdropFilter: "blur(10px)",
          }}
        >
          <div style={{ color: "#00e5ff", fontSize: 28, fontWeight: 900, letterSpacing: "0.08em" }}>
            MOTORS OFF · SENSORS ON
          </div>
          <div style={{ color: "#e0f2fe", fontSize: 16, fontWeight: 500, marginTop: 4 }}>
            Tidal Drift Station-Keeping · Micro-Thrust Position Corrections
          </div>
        </div>
      )}

      {/* 4. SCENE 2: 10× LESS POWER COMPARISON CARD (0:55 - 1:02) */}
      {t >= 55.0 && t < 62.0 && (
        <div
          style={{
            position: "absolute",
            bottom: 48,
            right: 48,
            width: 440,
            background: "rgba(10, 22, 35, 0.94)",
            border: "1px solid rgba(56, 189, 248, 0.4)",
            borderRadius: 12,
            padding: "24px 28px",
            boxShadow: "0 12px 40px rgba(0, 0, 0, 0.6)",
            backdropFilter: "blur(12px)",
          }}
        >
          <div style={{ color: "#38bdf8", fontSize: 14, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Validated Energy Model
          </div>
          <div style={{ color: "#ffffff", fontSize: 32, fontWeight: 900, margin: "6px 0 14px" }}>
            10× LESS POWER
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", color: "#94a3b8" }}>
              <span>Continuous Motor Cruise:</span>
              <span style={{ color: "#f87171", fontWeight: 700 }}>100% Load (~6 Hours)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "#94a3b8" }}>
              <span>Drift Hotel Load (energy.toml):</span>
              <span style={{ color: "#4ade80", fontWeight: 700 }}>10% Load (Days at Sea)</span>
            </div>
          </div>
        </div>
      )}

      {/* 5. SCENE 2: BOAT FAILURE & GAP COVERAGE NOTIFICATION (1:03 - 1:12) */}
      {t >= 63.0 && t < 72.0 && (
        <div
          style={{
            position: "absolute",
            bottom: 48,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(15, 23, 42, 0.94)",
            border: "1px solid #ef4444",
            boxShadow: "0 0 30px rgba(239, 68, 68, 0.35)",
            borderRadius: 12,
            padding: "20px 36px",
            textAlign: "center",
          }}
        >
          <div style={{ color: "#ef4444", fontSize: 16, fontWeight: 800, letterSpacing: "0.08em" }}>
            SIMULATED FAILURE: USV-01 OFFLINE
          </div>
          <div style={{ color: "#ffffff", fontSize: 24, fontWeight: 800, marginTop: 4 }}>
            Swarm Automatically Covers Gap → USV-04 Assigned
          </div>
          <div style={{ color: "#94a3b8", fontSize: 14, marginTop: 4 }}>
            Zero manual operator intervention required
          </div>
        </div>
      )}

      {/* 6. SCENE 2: 30 TESTS · 0 VIOLATIONS BADGE (1:12 - 1:15) */}
      {t >= 72.0 && t < 75.0 && (
        <div
          style={{
            position: "absolute",
            top: 100,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(6, 30, 20, 0.95)",
            border: "2px solid #22c55e",
            boxShadow: "0 0 30px rgba(34, 197, 94, 0.4)",
            padding: "20px 48px",
            borderRadius: 12,
            textAlign: "center",
          }}
        >
          <div style={{ color: "#22c55e", fontSize: 32, fontWeight: 900, letterSpacing: "0.04em" }}>
            30 TESTS · 0 RESERVE VIOLATIONS
          </div>
          <div style={{ color: "#bbf7d0", fontSize: 16, fontWeight: 600, marginTop: 4 }}>
            Validated Simulation Data (world/endurance.py)
          </div>
        </div>
      )}

      {/* 7. SCENE 3: EXPLAINABLE DECISION CALLOUT (1:15 - 1:30) */}
      {t >= 75.0 && t < 90.0 && (
        <div
          style={{
            position: "absolute",
            bottom: 48,
            right: 48,
            width: 480,
            background: "rgba(10, 22, 35, 0.95)",
            border: "1px solid #38bdf8",
            borderRadius: 12,
            padding: "22px 28px",
            boxShadow: "0 12px 40px rgba(0, 0, 0, 0.6)",
          }}
        >
          <div style={{ color: "#38bdf8", fontSize: 13, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Autonomous Assignment Reason (agent/auction.py)
          </div>
          <div style={{ color: "#ffffff", fontSize: 20, fontWeight: 800, margin: "8px 0" }}>
            USV-04 assigned to Sector C
          </div>
          <div
            style={{
              background: "rgba(56, 189, 248, 0.1)",
              borderLeft: "3px solid #38bdf8",
              padding: "8px 12px",
              color: "#e0f2fe",
              fontSize: 14,
              fontFamily: "monospace",
              margin: "8px 0",
            }}
          >
            "USV 04: cheapest of 2 bids (USV 02 +12m); 4 min away, battery ~6h after [battery return]"
          </div>
          <div style={{ color: "#94a3b8", fontSize: 13 }}>
            The watch officer gets one clear line: who took over, and why.
          </div>
        </div>
      )}

      {/* 8. SCENE 3: RELAY REPLACEMENT NOTIFICATION (1:30 - 1:42) */}
      {t >= 90.0 && t < 102.0 && (
        <div
          style={{
            position: "absolute",
            top: 100,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(15, 23, 42, 0.94)",
            border: "1px solid #f59e0b",
            boxShadow: "0 0 30px rgba(245, 158, 11, 0.3)",
            padding: "18px 40px",
            borderRadius: 12,
            textAlign: "center",
          }}
        >
          <div style={{ color: "#f59e0b", fontSize: 15, fontWeight: 800, letterSpacing: "0.08em" }}>
            RELAY VESSEL USV-05 LOST
          </div>
          <div style={{ color: "#ffffff", fontSize: 26, fontWeight: 900, marginTop: 4 }}>
            USV-03 Automatically Elected as New Relay
          </div>
          <div style={{ color: "#94a3b8", fontSize: 14, marginTop: 4 }}>
            Comms mesh dynamically reconfigures · Cable sweep continues
          </div>
        </div>
      )}

      {/* 9. SCENE 3: SHORE LINK CUT & RECONCILIATION (1:42 - 1:53) */}
      {t >= 102.0 && t < 113.0 && (
        <div
          style={{
            position: "absolute",
            bottom: 48,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(15, 23, 42, 0.94)",
            border: t < 108 ? "1px solid #ef4444" : "1px solid #22c55e",
            boxShadow: t < 108 ? "0 0 30px rgba(239, 68, 68, 0.3)" : "0 0 30px rgba(34, 197, 94, 0.3)",
            padding: "18px 40px",
            borderRadius: 12,
            textAlign: "center",
          }}
        >
          {t < 108 ? (
            <>
              <div style={{ color: "#ef4444", fontSize: 15, fontWeight: 800, letterSpacing: "0.08em" }}>
                COMMUNICATION TO SHORE SEVERED
              </div>
              <div style={{ color: "#ffffff", fontSize: 24, fontWeight: 800, marginTop: 4 }}>
                Boats Continue Patrol Autonomously · Store & Forward Buffer Active
              </div>
            </>
          ) : (
            <>
              <div style={{ color: "#22c55e", fontSize: 15, fontWeight: 800, letterSpacing: "0.08em" }}>
                SHORE LINK RESTORED
              </div>
              <div style={{ color: "#ffffff", fontSize: 24, fontWeight: 800, marginTop: 4 }}>
                Synchronizing Swarm Telemetry & Task Logs
              </div>
            </>
          )}
        </div>
      )}

      {/* 10. SCENE 4: SLOTTED AUCTION FORMULA (1:58 - 2:25) */}
      {t >= 118.0 && t < 144.0 && (
        <div
          style={{
            position: "absolute",
            top: 100,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(10, 22, 35, 0.94)",
            border: "1px solid rgba(56, 189, 248, 0.5)",
            boxShadow: "0 12px 40px rgba(0, 0, 0, 0.6)",
            borderRadius: 12,
            padding: "20px 48px",
            textAlign: "center",
          }}
        >
          <div style={{ color: "#38bdf8", fontSize: 14, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase" }}>
            Distributed Slotted Auction (agent/auction.py)
          </div>
          <div style={{ color: "#ffffff", fontSize: 28, fontWeight: 900, margin: "8px 0" }}>
            TOTAL COST = ENERGY / TIME COST + COVERAGE RISK
          </div>
          <div style={{ color: "#7dd3fc", fontSize: 15, fontWeight: 500 }}>
            No Central Auctioneer · Peer-to-Peer Bid Gossip · Consensus Guaranteed
          </div>
        </div>
      )}

      {/* 11. SCENE 4: ARDUPILOT & RETROFIT HARDWARE ARCHITECTURE (2:25 - 2:34) */}
      {t >= 144.0 && t < 154.0 && (
        <div
          style={{
            position: "absolute",
            bottom: 48,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(10, 24, 38, 0.96)",
            border: "2px solid #00e5ff",
            boxShadow: "0 0 40px rgba(0, 229, 255, 0.35)",
            borderRadius: 14,
            padding: "24px 48px",
            textAlign: "center",
          }}
        >
          <div style={{ color: "#00e5ff", fontSize: 32, fontWeight: 900, letterSpacing: "0.06em" }}>
            ARDUPILOT COMPATIBLE · MAVLink
          </div>
          <div style={{ color: "#ffffff", fontSize: 22, fontWeight: 800, margin: "8px 0" }}>
            A computer the size of a phone · EUR 2,500–4,500 retrofit box
          </div>
          <div style={{ color: "#94a3b8", fontSize: 18, fontWeight: 700, letterSpacing: "0.08em" }}>
            NO GPUs · NO NEW HULL · WORKS ON ANY BOAT
          </div>
        </div>
      )}

      {/* 12. SCENE 5: THE THREE CLOSING STATEMENTS (2:43 - 2:55) */}
      {t >= 163.0 && t < 175.0 && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 20,
          }}
        >
          {t >= 163.0 && (
            <div
              style={{
                background: "rgba(7, 18, 28, 0.92)",
                border: "2px solid #00e5ff",
                boxShadow: "0 0 30px rgba(0, 229, 255, 0.3)",
                padding: "16px 48px",
                borderRadius: 12,
                color: "#ffffff",
                fontSize: 42,
                fontWeight: 900,
                letterSpacing: "0.04em",
              }}
            >
              DAYS AT SEA
            </div>
          )}
          {t >= 167.0 && (
            <div
              style={{
                background: "rgba(7, 18, 28, 0.92)",
                border: "2px solid #38bdf8",
                boxShadow: "0 0 30px rgba(56, 189, 248, 0.3)",
                padding: "16px 48px",
                borderRadius: 12,
                color: "#ffffff",
                fontSize: 42,
                fontWeight: 900,
                letterSpacing: "0.04em",
              }}
            >
              ONE OPERATOR
            </div>
          )}
          {t >= 171.0 && (
            <div
              style={{
                background: "rgba(7, 18, 28, 0.92)",
                border: "2px solid #22c55e",
                boxShadow: "0 0 30px rgba(34, 197, 94, 0.3)",
                padding: "16px 48px",
                borderRadius: 12,
                color: "#ffffff",
                fontSize: 42,
                fontWeight: 900,
                letterSpacing: "0.04em",
              }}
            >
              A DETECTION BOX
            </div>
          )}
        </div>
      )}

      {/* 13. SCENE 5: FINAL BRAND SCREEN & TAGLINE (2:55 - 3:00) */}
      {t >= 175.0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "#04090f",
            opacity: Math.min(1, (t - 175.0) / 1.5),
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            textAlign: "center",
            padding: "40px",
          }}
        >
          {/* Logo Insignia */}
          <div
            style={{
              width: 96,
              height: 96,
              borderRadius: "50%",
              background: "linear-gradient(135deg, #00e5ff 0%, #0369a1 100%)",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              boxShadow: "0 0 60px rgba(0, 229, 255, 0.6)",
              marginBottom: 32,
            }}
          >
            <div style={{ width: 44, height: 44, border: "4px solid #ffffff", borderRadius: "50%", borderTopColor: "transparent" }} />
          </div>

          <div
            style={{
              color: "#ffffff",
              fontSize: 72,
              fontWeight: 900,
              letterSpacing: "0.06em",
              marginBottom: 16,
            }}
          >
            PHAROS
          </div>

          <div
            style={{
              color: "#7dd3fc",
              fontSize: 26,
              fontWeight: 600,
              maxWidth: 800,
              lineHeight: 1.4,
              letterSpacing: "0.01em",
            }}
          >
            Autonomous Protection for Critical Maritime Infrastructure
          </div>

          <div
            style={{
              position: "absolute",
              bottom: 48,
              color: "#475569",
              fontSize: 14,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            EDTH 2026 STARTUP PITCH · LIVE DEMO REPLAY
          </div>
        </div>
      )}
    </div>
  );
}
