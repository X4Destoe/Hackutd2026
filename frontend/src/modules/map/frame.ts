type Tick = (now: number) => void;

const ticks = new Set<Tick>();
let handle = 0;

function loop(now: number) {
  ticks.forEach((tick) => {
    try {
      tick(now);
    } catch {
      // Keep the shared loop alive if one paint update runs before its layer exists.
    }
  });
  handle = requestAnimationFrame(loop);
}

/** One animation loop for every map effect. Particles and paint updates share it. */
export function bindFrame(tick: Tick) {
  ticks.add(tick);
  if (!handle) handle = requestAnimationFrame(loop);
  return () => {
    ticks.delete(tick);
    if (ticks.size === 0) {
      cancelAnimationFrame(handle);
      handle = 0;
    }
  };
}
