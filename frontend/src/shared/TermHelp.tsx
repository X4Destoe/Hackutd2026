import { useState } from 'react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { Info } from 'lucide-react';
import './term-help.css';

const explanations: Record<string, string> = {
  'Estimated loss': 'Estimated money still at risk after insurance and approved protective actions. For example: $1M in expected losses − $600k insurance − $100k prevented = $300k remaining. This is a model, not a bill or guaranteed payout.',
  'Gross loss': 'Total modeled damage and business disruption before subtracting insurance recovery. Approved protective actions can reduce these losses.',
  'Avoided': 'Modeled loss prevented by approved protective actions. This is an estimated benefit, not money already received.',
  'Insurance recovery': 'The portion of modeled losses insurance may cover, subject to deductibles, coverage limits, and policy terms. It is not an approved claim or guaranteed payment.',
  'ROI': 'Return on investment. Here it means modeled loss prevented divided by action cost. A 5× ROI means a $1,000 action could prevent $5,000 in losses; it is not guaranteed profit.',
  'Tenant SLA': 'A service-level agreement is a promise in a tenant contract, such as reliable power. This amount estimates penalties if that promise is not met.',
  'Rent abatement': 'Rent a tenant may not owe while the property is unusable. This estimates the resulting lost rental income.',
  'Operations': 'Extra modeled costs of responding to the disruption, such as temporary services and emergency work.',
  'Money waterfall': 'A breakdown of the estimated loss: damage and disruption add costs; insurance subtracts the covered portion. The final line is the amount remaining.',
  'Grid': 'The outside electricity network supplying the building. A grid outage can affect the property even when the building itself is not damaged.',
  'Generator remaining': 'Estimated backup-generator runtime still available at this point in the scenario. It does not verify actual fuel, equipment condition, or working power.',
  'Flood / surge depth': 'Modeled water depth at the property. Flooding can come from rainfall; storm surge is seawater pushed inland by a storm. Live proxies are not measured building flood depths.',
  'Outage duration': 'How long the outside electricity supply is modeled to be unavailable. A generator may cover part of that time.',
  'Act by': 'The latest modeled time to start the action for its full benefit. Times are relative to disaster impact: −12h means 12 hours before; +12h means 12 hours after.',
  'Act by impact hour': 'The latest modeled time to start the action for its full benefit. 0h is disaster impact; negative hours are before impact and positive hours are after.',
  'Potential savings': 'Modeled losses this plan could prevent if carried out in time. These are estimated avoided costs, not a guaranteed cash payment.',
  'Would have saved': 'The loss this plan was modeled to prevent if started before its deadline. The deadline has passed, so this is a missed opportunity, not a current saving.',
  'Saves': 'Modeled losses this plan could prevent if carried out in time. Compare this amount with the action cost and deadline.',
  'Critical operations': 'Activities that are especially important to keep running, such as medical care or essential business services.',
};

/** Unknown labels stay plain; glossary entries share consistent, source-qualified copy. */
export default function TermHelp({ term }: { term: string }) {
  const [open, setOpen] = useState(false);
  const explanation = explanations[term];
  if (!explanation) return <>{term}</>;
  return <span className="term-label">{term}<Tooltip.Provider delayDuration={200}>
    <Tooltip.Root open={open} onOpenChange={setOpen}>
      <Tooltip.Trigger asChild>
        <button type="button" className="term-info" aria-label={`About ${term}`} aria-expanded={open}
          onPointerDown={event => event.preventDefault()}
          onClick={event => { event.preventDefault(); setOpen(value => !value); }}>
          <Info size={13} aria-hidden="true" />
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal><Tooltip.Content className="term-explanation" sideOffset={6} collisionPadding={12}>
        {explanation}<Tooltip.Arrow className="term-explanation-arrow" />
      </Tooltip.Content></Tooltip.Portal>
    </Tooltip.Root>
  </Tooltip.Provider></span>;
}
