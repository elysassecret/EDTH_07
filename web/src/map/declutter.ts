// Owner: C. Chart text never overlaps. Every label gets a box on screen (from its position,
// pixel offset, font size and text length). Going from the most to the least important, a
// label is drawn only if its box touches no box already kept. The rest come back when you zoom
// in and they move apart. A selected boat or contact always keeps its label. Re-run after every
// pan or zoom (Chart.tsx).

/** Higher wins. Safety-relevant text first, background names last. */
export const PRIORITY: Record<string, number> = {
  selected: 1000,
  boat: 100,
  "boat-stale": 95,
  dark: 80, // camera contact, no AIS
  docked: 70,
  spread: 60, // "could be within"
  age: 50, // cable segment age
  station: 40,
  stale: 35, // stale contact
  ais: 20, // AIS ship name
  cable: 10,
  geo: 0, // depth and infrastructure names
};

export interface Box { x: number; y: number; w: number; h: number }

// average glyph width of the UI sans font, as a share of the font size, plus a small gap
const CHAR_W = 0.58;
const GAP_PX = 3;

/** Screen box of a centred label at pixel point x, y. */
export function textBox(x: number, y: number, text: string, size: number, off: [number, number]): Box {
  const w = text.length * size * CHAR_W + 2 * GAP_PX;
  const h = size * 1.2 + 2 * GAP_PX;
  return { x: x + off[0] - w / 2, y: y + off[1] - h / 2, w, h };
}

const overlaps = (a: Box, b: Box) =>
  a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

/** Which labels to draw: true = keep. Ties go to the earlier label, so the result is stable. */
export function keepNonOverlapping(items: { box: Box; p: number }[]): boolean[] {
  const order = items.map((_, i) => i).sort((a, b) => items[b].p - items[a].p || a - b);
  const kept: Box[] = [];
  const keep = items.map(() => false);
  for (const i of order) {
    if (kept.some((k) => overlaps(k, items[i].box))) continue;
    kept.push(items[i].box);
    keep[i] = true;
  }
  return keep;
}
