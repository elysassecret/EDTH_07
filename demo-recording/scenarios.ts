/** Deterministic simulation scenarios and parameters for PHAROS pitch recording */
export interface DemoScenarioConfig {
  seed: number;
  start_s: number;
  start_paused: boolean;
  warp_between: number;
  warp_near: number;
  scripted_events: {
    t_sim_s: number;
    kind: string;
    boat?: number;
    description: string;
  }[];
}

export const PITCH_DEMO_SCENARIO: DemoScenarioConfig = {
  seed: 1,
  start_s: 6900, // fast-forward: opens 5 min (sim) before battery event
  start_paused: true,
  warp_between: 240,
  warp_near: 6,
  scripted_events: [
    { t_sim_s: 7200, kind: "battery_low", boat: 1, description: "USV 01 battery low -> RTB Korsør" },
    { t_sim_s: 7320, kind: "link_cut", boat: 4, description: "USV 04 shore link cut, routes via USV 05" },
    { t_sim_s: 11100, kind: "boat_off", boat: 5, description: "USV 05 relay lost -> USV 03 elected as relay" },
  ],
};
