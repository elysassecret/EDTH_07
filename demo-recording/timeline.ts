import timelineData from "./timeline.json";

export interface TimelinePhase {
  t: number;
  action: string;
  overlay: string;
}

export interface TimelineScene {
  id: string;
  speaker: "FRANKO" | "SIME" | "JAVIER" | "ALEX";
  start: number;
  end: number;
  duration: number;
  title: string;
  phases: TimelinePhase[];
}

export const TIMELINE: TimelineScene[] = timelineData as TimelineScene[];

export function getTotalDuration(scenes: TimelineScene[] = TIMELINE): number {
  return scenes.reduce((sum, s) => sum + s.duration, 0);
}

export function getSceneAt(tSeconds: number, scenes: TimelineScene[] = TIMELINE): TimelineScene | undefined {
  return scenes.find((s) => tSeconds >= s.start && tSeconds < s.end) ?? scenes[scenes.length - 1];
}
