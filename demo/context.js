// Offline map backdrop: APPROXIMATE major highways and Gulf water, only used when map tiles can't load.
/* eslint-disable */
(function () {
  const ring = (c, rMi, n = 96) => {
    const kx = Math.cos(c[1] * Math.PI / 180) * 69, pts = [];
    for (let i = 0; i <= n; i++) { const a = (i / n) * 2 * Math.PI; pts.push([c[0] + Math.cos(a) * rMi / kx, c[1] + Math.sin(a) * rMi / 69]); }
    return pts;
  };
  const road = (coords) => ({ type: "Feature", properties: { k: "road" }, geometry: { type: "LineString", coordinates: coords } });
  window.BRACE_CONTEXT = { type: "FeatureCollection", features: [
    // Houston: 610 Loop, Beltway 8, I-10, I-45, I-69
    road(ring([-95.42, 29.76], 5.2)), road(ring([-95.44, 29.74], 12.5)),
    road([[-95.85, 29.78], [-95.42, 29.775], [-95.05, 29.77]]),
    road([[-95.45, 30.05], [-95.37, 29.76], [-95.10, 29.45]]),
    road([[-95.75, 29.58], [-95.37, 29.75], [-95.18, 29.97]]),
    // Dallas: I-635 / I-20 ring, I-35E, I-30, US-75
    road(ring([-96.80, 32.81], 10.5)),
    road([[-96.92, 33.10], [-96.80, 32.78], [-96.84, 32.55]]),
    road([[-97.10, 32.75], [-96.80, 32.77], [-96.55, 32.86]]),
    road([[-96.80, 32.78], [-96.71, 33.06]]),
    // Fort Myers: I-75, US-41
    road([[-81.74, 26.95], [-81.77, 26.62], [-81.75, 26.28]]),
    road([[-81.88, 26.80], [-81.87, 26.64], [-81.80, 26.33]]),
    { type: "Feature", properties: { k: "water" }, geometry: { type: "Polygon", coordinates: [[
      [-82.70, 26.10], [-82.70, 27.10], [-82.20, 27.10], [-82.10, 26.80], [-82.04, 26.62], [-82.00, 26.52],
      [-81.97, 26.47], [-81.92, 26.44], [-81.86, 26.39], [-81.80, 26.33], [-81.76, 26.24], [-81.72, 26.10], [-82.70, 26.10]]] } },
  ] };
})();
