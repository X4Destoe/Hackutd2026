import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Shuffle, X } from "lucide-react";
import { Button } from "../../shared/ui";
import { invalidateKeys, scenarioKeys } from "../../shared/queries";
import "./simulation.css";

type Configuration = { city: string; disaster: string; water_ft: number; wind_mph: number; outage_hours: number; temperature_f: number; ice_in: number };
type Options = { cities: { id: string; name: string }[]; disasters: { id: string; name: string; cities: string[] }[]; disclaimer: string };
async function request<T>(path: string, body?: Configuration): Promise<T> {
  const response = await fetch(`/api/simulation/${path}`, { method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(typeof detail.detail === "string" ? detail.detail : "Simulation service is unavailable. Your choices are kept; please retry.");
  }
  return response.json();
}

export default function SimulationBuilder() {
  const [open, setOpen] = useState(false);
  const [configuration, setConfiguration] = useState<Configuration>({ city: "houston", disaster: "flood", water_ft: 6, wind_mph: 100, outage_hours: 24, temperature_f: 10, ice_in: 0.5 });
  const options = useQuery({ queryKey: ["simulationOptions"], queryFn: () => request<Options>("options"), enabled: open });
  const cache = useQueryClient();
  const start = useMutation({ mutationFn: () => request("start", configuration), onSuccess: async () => {
    await invalidateKeys(cache, [...scenarioKeys, "scenarios"]); setOpen(false);
  } });
  const pickCity = (city: string) => setConfiguration(current => ({ ...current, city,
    disaster: options.data?.disasters.find(disaster => disaster.id === current.disaster)?.cities.includes(city) ? current.disaster : "flood" }));
  const control = (key: keyof Configuration, label: string, min: number, max: number, step: number, unit: string) => <label className="simulation-control">
    <span>{label}<output>{configuration[key]} {unit}</output></span>
    <input type="range" aria-label={label} min={min} max={max} step={step} value={configuration[key]}
      onChange={event => setConfiguration(current => ({ ...current, [key]: Number(event.target.value) }))} disabled={start.isPending} />
  </label>;
  return <Dialog.Root open={open} onOpenChange={value => { if (!start.isPending) setOpen(value); }}>
    <Dialog.Trigger asChild><Button variant="outline">Build simulation</Button></Dialog.Trigger>
    <Dialog.Portal><Dialog.Overlay className="simulation-backdrop" />
      <Dialog.Content className="simulation-dialog">
        <Dialog.Title>Build a disaster simulation</Dialog.Title>
        <Dialog.Description>Choose a supported city and hypothetical effects. Running starts a fresh scenario and clears its prior plans, messages and work orders.</Dialog.Description>
        <Dialog.Close asChild><Button variant="ghost" className="simulation-close" aria-label="Close simulation builder" disabled={start.isPending}><X size={18} /></Button></Dialog.Close>
        {options.isPending ? <p role="status">Loading supported cities…</p> : options.isError ? <div role="alert"><p>Simulation options are unavailable.</p><Button onClick={() => void options.refetch()}>Retry simulation options</Button></div> : <form onSubmit={event => { event.preventDefault(); start.mutate(); }}>
          <label>City<select aria-label="Simulation city" value={configuration.city} onChange={event => pickCity(event.target.value)} disabled={start.isPending}>
            {options.data.cities.map(city => <option key={city.id} value={city.id}>{city.name}</option>)}
          </select></label>
          <Button variant="outline" disabled={start.isPending} onClick={() => {
            const cities = options.data.cities; if (cities.length) pickCity(cities[Math.floor(Math.random() * cities.length)].id);
          }}><Shuffle size={14} /> Pick a random city</Button>
          <label>Disaster<select aria-label="Simulation disaster" value={configuration.disaster} onChange={event => setConfiguration(current => ({ ...current, disaster: event.target.value }))} disabled={start.isPending}>
            {options.data.disasters.filter(disaster => disaster.cities.includes(configuration.city)).map(disaster => <option key={disaster.id} value={disaster.id}>{disaster.name}</option>)}
          </select></label>
          {["flood", "hurricane", "surge"].includes(configuration.disaster) && control("water_ft", "Peak water at exercise center", 0, 20, 0.5, "ft")}
          {["windstorm", "hurricane"].includes(configuration.disaster) && control("wind_mph", "Peak wind speed", 0, 180, 5, "mph")}
          {configuration.disaster === "winter" && <>{control("temperature_f", "Minimum temperature", -30, 32, 1, "°F")}{control("ice_in", "Ice accumulation", 0, 2, 0.1, "in")}</>}
          {control("outage_hours", "Utility outage duration", 0, 168, 6, "hours")}
          <p className="simulation-disclaimer">{options.data.disclaimer} Buildings and financial estimates use the existing fictional portfolio. Storm surge is offered only for Fort Myers.</p>
          {start.isError && <p role="alert">{start.error.message}</p>}
          <Button type="submit" disabled={start.isPending}>{start.isPending ? "Starting simulation…" : "Run custom simulation"}</Button>
        </form>}
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
