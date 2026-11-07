// Shared transport freshness policy for the operator console and evaluator viewer.
// Polling/rendering headroom sits inside the plan's two-second lost-feed bound.
export const FEED_STALE_MS = 1500;
export const FEED_POLL_MS = 200;
export function feedExpired(receivedAt: number | null, now: number) {
  return receivedAt === null || now - receivedAt >= FEED_STALE_MS;
}
