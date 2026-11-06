// Owner: C. Calm ECDIS-dusk-like palette. Colour is always paired with a shape or a word.
type RGB = [number, number, number];
export type RGBA = [number, number, number, number];

export const SEA = "#16222d";
export const LAND = "#3a3a30";
export const BOX = "#c9d3dc";
export const CABLE_POWER = "#c85bb4"; // ECDIS cables are magenta
export const CABLE_DATA = "#a07cc8";
export const LANE = "#8aa0b2";

const rgb = (c: RGB, a = 255): RGBA => [c[0], c[1], c[2], a];

// NATO-style track colours: friend blue, neutral green, unknown yellow.
export const FRIEND: RGB = [96, 170, 255];
export const NEUTRAL: RGB = [110, 200, 120];
export const UNKNOWN: RGB = [240, 210, 80];
export const STALE: RGB = [130, 136, 142];
export const TEXT: RGB = [222, 228, 234];
export const SHORE: RGB = [220, 220, 220];

export const c = rgb;
