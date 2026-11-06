// Owner: C. Message shapes sent by server/mock_feed.py.
// Hand-written until contract/schema.json exists; then replaced by the generated contract.ts.
// All times are sim seconds since t0_utc.

export type Mode =
  | "PATROL" | "ECO" | "SENTINEL" | "DORMANT" | "SHADOWING" | "RETURNING" | "UNAVAILABLE";
export type LinkStatus = "direct" | "relay" | "none";
export type LatLon = [number, number];

export interface Boat {
  id: number;
  name: string;
  x: number;
  y: number;
  lat: number;
  lon: number;
  hdg: number; // degrees true
  sog_kn: number;
  mode: Mode;
  role: string;
  batt: number; // permille
  endurance_s: number;
  must_return_by: number;
  link: LinkStatus;
  via: number | "shore" | null;
  tour: string[];
  last_heard: number | null;
}

export interface Contact {
  id: string;
  lat: number;
  lon: number;
  cog: number;
  sog_kn: number;
  ais: boolean;
  name: string | null;
  source: "ais" | "camera" | "fused";
  seen_by: number[];
  last_seen: number | null;
  trail: LatLon[];
  name_status: string;
  anchor_status: string;
  detected?: boolean; // truth channel only
}

export interface Task { v: number; owner: number; deputy: number; state: 0 | 1 | 2 }
export interface Link { a: number; b: number | "shore"; ok: boolean; m: number | null }

export interface Decision {
  id: string;
  tier: "delegated" | "held";
  kind: string;
  text: string;
  boat: number;
  contact: string | null;
  actions: ("confirm" | "stop" | "approve" | "decline")[];
  created: number;
  status: string;
  route: LatLon[] | null;
  answered?: number;
}

export interface Alert {
  key: string;
  level: "alarm" | "warning" | "caution";
  text: string;
  t: number;
  active: boolean;
  acked: boolean;
}

export interface LogEvent { t: number; kind: string; text: string; exercise: boolean }

export interface Snapshot {
  type: "snapshot";
  schema: number;
  source: string;
  channel: "shore" | "truth";
  seed: number;
  t: number;
  t0_utc: string;
  speed: number;
  boats: Boat[];
  tasks: Record<string, Task>;
  seg_age: Record<string, number>;
  links: Link[];
  contacts: Contact[];
  decisions: Decision[];
  alerts: Alert[];
  events: LogEvent[];
}

export interface SceneMsg {
  type: "scene";
  schema: number;
  source: string;
  t0_utc: string;
  segments: Record<string, LatLon[]>;
  stations: Record<string, LatLon>;
  shore: LatLon;
  stale_after_s: number;
  horizon_s: number;
}

export interface Ack { type: "ack"; cmd: string | null; id: string | null; ok: boolean; error?: string }

export type Command =
  | { cmd: "confirm" | "stop" | "approve" | "decline" | "ack"; id: string }
  | { cmd: "inject"; kind: "battery_low" | "link_off" | "link_on" | "boat_off"; a: number; b?: number | "shore" }
  | { cmd: "speed"; value: number | "auto" }
  | { cmd: "pause"; on?: boolean }
  | { cmd: "reset"; seed?: number };
