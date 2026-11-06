// GENERATED from contract/schema.json by pnpm gen:contract. Do not edit.

export type Command = Decide | Inject | AckAlert;
export type Cmd = "confirm" | "stop" | "approve" | "decline";
export type Id = string;
export type A = number;
export type B = number | "shore" | null;
export type Cmd1 = "inject";
export type Kind = "battery_low" | "link_off" | "link_on" | "boat_off";
export type Cmd2 = "ack";
export type Id1 = string;
export type Ack = boolean;
export type Id2 = string;
export type Level = "alarm" | "warning" | "caution";
export type T = number;
export type Text = string;
export type Alerts = Alert[];
export type Batt = number;
export type EnduranceS = number;
export type Hdg = number;
export type Id3 = number;
export type LastHeard = number;
export type Lat = number;
export type Link = "direct" | "peer" | "none";
export type Lon = number;
export type Mode = string;
export type MustReturnBy = number | null;
export type Roles = string[];
export type Sog = number;
export type Tour = string[];
export type Via = number | null;
export type X = number;
export type Y = number;
export type Boats = Boat[];
export type Ais = boolean;
export type Cog = number;
export type Course = number | null;
export type FirstSeen = number;
export type Anchor = boolean;
export type CannotHold = boolean;
export type Capped = boolean;
export type Dwell = boolean;
export type Name = boolean;
export type Id4 = string;
export type LastSeen = number;
export type Lat1 = number;
export type Lon1 = number;
export type Name1 = string | null;
export type SeenBy = number[];
export type Sog1 = number;
export type Source = "ais" | "camera" | "fused";
export type State = number;
export type Track = string;
export type Trail = [unknown, unknown][];
export type Watcher = number;
export type X1 = number;
export type Y1 = number;
export type Contacts = Contact[];
export type Actions = ("confirm" | "stop" | "approve" | "decline")[];
export type Boat1 = number;
export type Dec = string;
export type Id5 = string;
export type Route = [unknown, unknown][] | null;
export type State1 = "pending" | "approved" | "declined" | "delivered" | "expired" | "confirmed" | "stopped";
export type T1 = number;
export type Task = string;
export type Text1 = string;
export type Tier = "delegated" | "held";
export type Decisions = Decision[];
export type Exercise = boolean;
export type Kind1 = string;
export type T2 = number;
export type Text2 = string;
export type Events = Event[];
export type A1 = number;
export type B1 = number;
export type State2 = "up" | "down" | "cut";
export type Links = Link1[];
export type SchemaVersion = number;
export type Speed = number;
export type T3 = number;
export type T0Utc = string;
export type Deputy = number;
export type Owner = number;
export type State3 = number;
export type V = number;
export type View = "shore" | "truth";

/**
 * Root of the exported schema, so one file carries every type.
 */
export interface Contract {
  command: Command;
  snapshot: Snapshot;
}
export interface Decide {
  cmd: Cmd;
  id: Id;
}
export interface Inject {
  a: A;
  b?: B;
  cmd: Cmd1;
  kind: Kind;
}
export interface AckAlert {
  cmd: Cmd2;
  id: Id1;
}
export interface Snapshot {
  alerts: Alerts;
  boats: Boats;
  contacts: Contacts;
  decisions: Decisions;
  events: Events;
  links: Links;
  schema_version?: SchemaVersion;
  seg_age: SegAge;
  speed: Speed;
  t: T3;
  t0_utc?: T0Utc;
  tasks: Tasks;
  view: View;
}
export interface Alert {
  ack?: Ack;
  id: Id2;
  level: Level;
  t: T;
  text: Text;
}
export interface Boat {
  batt: Batt;
  endurance_s: EnduranceS;
  hdg?: Hdg;
  id: Id3;
  last_heard: LastHeard;
  lat: Lat;
  link: Link;
  lon: Lon;
  mode: Mode;
  must_return_by?: MustReturnBy;
  roles: Roles;
  sog?: Sog;
  tour: Tour;
  via?: Via;
  x: X;
  y: Y;
}
export interface Contact {
  ais: Ais;
  cog: Cog;
  course?: Course;
  first_seen: FirstSeen;
  flags: ContactFlags;
  id: Id4;
  last_seen: LastSeen;
  lat: Lat1;
  lon: Lon1;
  name?: Name1;
  seen_by: SeenBy;
  sog: Sog1;
  source?: Source;
  state: State;
  track: Track;
  trail?: Trail;
  watcher: Watcher;
  x: X1;
  y: Y1;
}
export interface ContactFlags {
  anchor?: Anchor;
  cannot_hold?: CannotHold;
  capped?: Capped;
  dwell?: Dwell;
  name?: Name;
}
export interface Decision {
  actions?: Actions;
  boat?: Boat1;
  dec: Dec;
  id: Id5;
  route?: Route;
  state: State1;
  t: T1;
  task: Task;
  text: Text1;
  tier?: Tier;
}
export interface Event {
  exercise?: Exercise;
  kind: Kind1;
  t: T2;
  text: Text2;
}
export interface Link1 {
  a: A1;
  b: B1;
  state: State2;
}
export interface SegAge {
  [k: string]: number;
}
export interface Tasks {
  [k: string]: TaskView;
}
export interface TaskView {
  deputy: Deputy;
  owner: Owner;
  state: State3;
  v: V;
}
