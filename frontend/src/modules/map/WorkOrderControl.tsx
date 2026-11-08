import { useState } from "react";
import type { Model } from "../../shared/api";
import { useUpdateWorkOrder } from "../../shared/queries";
import { Button } from "../../shared/ui";

/** Coordinator updates use the same public API and event stream as technician replies. */
export default function WorkOrderControl({ order }: { order: Model<"WorkOrder"> }) {
  const update = useUpdateWorkOrder();
  const [status, setStatus] = useState<"accepted" | "blocked" | "done">("accepted");
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState("");
  return <details className="map-workorder">
    <summary><span>{order.action_code.replaceAll("_", " ")}</span><b>{order.status}</b></summary>
    <p>{order.id} · Assignee {order.party_id}</p>
    {!!order.updates?.length && <ul aria-label={`Updates for ${order.id}`}>
      {order.updates.map((text, i) => <li key={i}>{text}</li>)}
    </ul>}
    {order.status !== "done" && <form onSubmit={event => {
      event.preventDefault();
      if (update.isPending) return;
      setNotice("");
      update.mutate({ id: order.id, status, note: note.trim() || "Coordinator status update from map." }, {
        onSuccess: () => { setNotice(`Saved: ${status}.`); setNote(""); },
        onError: () => setNotice("Update failed. Your note is kept; retry when connected."),
      });
    }}>
      <label>Status<select aria-label={`Status for ${order.id}`} value={status} disabled={update.isPending}
        onChange={event => setStatus(event.target.value as typeof status)}>
        <option value="accepted">Accepted</option><option value="blocked">Blocked</option><option value="done">Done</option>
      </select></label>
      <label>{status === "blocked" ? "Blocker and next step (required)" : "Progress or completion note"}
        <textarea aria-label={`Note for ${order.id}`} value={note} required={status === "blocked"} maxLength={1000}
          disabled={update.isPending} placeholder={status === "blocked" ? "What is preventing this task? What is needed next?" : "Record what was checked or completed."}
          onChange={event => setNote(event.target.value)} />
      </label>
      <Button type="submit" disabled={update.isPending || (status === "blocked" && !note.trim())}>
        {update.isPending ? "Saving…" : "Save work-order update"}
      </Button>
    </form>}
    {notice && <p role={update.isError ? "alert" : "status"}>{notice}</p>}
  </details>;
}
