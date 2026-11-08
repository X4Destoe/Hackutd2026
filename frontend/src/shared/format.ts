export type RiskLevel = 'none' | 'low' | 'moderate' | 'high' | 'severe';
export type Phase = 'forecast' | 'impact' | 'recovery';
export function money(cents: number): string {
  const dollars = Math.abs(cents) / 100;
  const [value, suffix] = dollars >= 1e9 ? [dollars / 1e9, 'B'] : dollars >= 1e6 ? [dollars / 1e6, 'M'] : dollars >= 1e3 ? [dollars / 1e3, 'k'] : [dollars, ''];
  return `${cents < 0 ? '−' : ''}$${new Intl.NumberFormat('en-US', { maximumFractionDigits: suffix ? 2 : 0 }).format(value)}${suffix}`;
}
export function hours(h: number): string { return `${h < 0 ? '−' : h > 0 ? '+' : ''}${Math.abs(h) >= 48 && h % 24 === 0 ? `${Math.abs(h) / 24}d` : `${Math.abs(h)}h`}`; }
export const riskColor = (level: RiskLevel): string => ({ none: '#94a3b8', low: '#22a06b', moderate: '#eab308', high: '#f97316', severe: '#dc2626' })[level];
export const phaseColor = (phase: Phase): string => ({ forecast: '#7c3aed', impact: '#dc2626', recovery: '#16834a' })[phase];
