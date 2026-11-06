// Owner: C. Nautical/UTC formatting. Sim time t (s) is shown as UTC "Z" time from t0_utc.

export function utc(t0: string, t: number): string {
  const d = new Date(Date.parse(t0) + Math.round(t * 1000));
  return d.toISOString().slice(11, 19) + "Z";
}

export function hhmm(t0: string, t: number): string {
  return utc(t0, t).slice(0, 5) + "Z";
}

/** 754 s -> "12:34" (mm:ss), 4000 s -> "1:06:40". */
export function dur(s: number): string {
  const v = Math.max(0, Math.round(s));
  const h = Math.floor(v / 3600);
  const m = Math.floor((v % 3600) / 60);
  const sec = v % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(sec).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** Endurance as "2 h 10 min". */
export function hm(s: number): string {
  const v = Math.max(0, Math.round(s / 60));
  return `${Math.floor(v / 60)} h ${String(v % 60).padStart(2, "0")} min`;
}

export const deg = (d: number) => `${String(Math.round(d) % 360).padStart(3, "0")}°`;
