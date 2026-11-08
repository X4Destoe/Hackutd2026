import { useMemo, useState } from "react";
import {
  useBuildings,
  useMessages,
  useMessagingStatus,
  useSimulateMessage,
} from "../../../../shared/queries";
import { Badge, Button } from "../../../../shared/ui";
function mediaLink(value: string): string | null {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}
export default function Messages() {
  const messages = useMessages();
  const status = useMessagingStatus();
  const buildings = useBuildings();
  const simulate = useSimulateMessage();
  const [party, setParty] = useState("resident");
  const [phone, setPhone] = useState("");
  const [text, setText] = useState("");
  const [media, setMedia] = useState("");
  const [error, setError] = useState("");
  const parties = useMemo(() => {
    const options = new Map<string, string>([["MGR-01", "Portfolio manager"]]);
    for (const b of buildings.data ?? []) {
      options.set(
        b.onsite_party_id,
        `${b.onsite_party_id} · ${b.city} engineer`,
      );
      for (const t of b.tenants ?? [])
        options.set(t.contact_party_id ?? t.id, `${t.name} contact`);
    }
    return [...options];
  }, [buildings.data]);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!text.trim()) {
      setError("Enter a message.");
      return;
    }
    if (party === "resident" && !/^\+[1-9]\d{7,14}$/.test(phone.trim())) {
      setError("Enter a phone number with country code, such as +12145550100.");
      return;
    }
    if (media && !mediaLink(media)) {
      setError("Photo URL must use http or https.");
      return;
    }
    simulate.mutate(
      {
        ...(party === "resident"
          ? { phone: phone.trim() }
          : { party_id: party }),
        text: text.trim(),
        ...(media ? { media_url: media } : {}),
      },
      {
        onSuccess: () => {
          setText("");
          setMedia("");
        },
        onError: () =>
          setError(
            "Message could not be submitted. Your draft is preserved; please retry.",
          ),
      },
    );
  };
  return (
    <div className="community-view">
      <h2>Texts</h2>
      <p className="panel-caption">
        {status.data
          ? `${status.data.mode === "photon" ? "Photon" : "Simulator"} · ${status.data.sent} sent · ${status.data.received} received`
          : "Messaging status unavailable"}
      </p>
      {status.data?.last_error && (
        <p role="alert">Channel issue: {status.data.last_error}</p>
      )}
      <form className="phone-simulator" onSubmit={submit}>
        <h3>Phone simulator</h3>
        <p>Send a demo reply or resident request to the response engine.</p>
        <label>
          Send as
          <select value={party} onChange={(e) => setParty(e.target.value)}>
            <option value="resident">Resident · enter phone</option>
            {parties.map(([id, label]) => (
              <option value={id} key={id}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {party === "resident" && (
          <label>
            Resident phone
            <input
              type="tel"
              autoComplete="off"
              placeholder="+12145550100"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </label>
        )}
        <label>
          Message
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={2000}
            rows={4}
            placeholder="Our apartment flooded, 2 kids, need a dry place"
            required
          />
        </label>
        <label>
          Photo URL (optional)
          <input
            type="url"
            value={media}
            onChange={(e) => setMedia(e.target.value)}
            placeholder="https://…"
          />
        </label>
        <Button type="submit" disabled={simulate.isPending}>
          {simulate.isPending ? "Submitting…" : "Send simulated message"}
        </Button>
        {error && <p role="alert">{error}</p>}
        {simulate.isSuccess && !error && (
          <p role="status">
            Message submitted. Responses and updates appear below.
          </p>
        )}
      </form>
      <h3 className="section-title">Message feed</h3>
      {messages.isPending ? (
        <p role="status">Loading messages…</p>
      ) : messages.isError ? (
        <p className="panel-empty">Message history is unavailable.</p>
      ) : messages.data.length === 0 ? (
        <p className="panel-empty">No messages yet.</p>
      ) : (
        <ol className="community-list">
          {[...messages.data].reverse().map((message) => (
            <li
              key={message.id}
              className={`community-card message-${message.direction}`}
            >
              <div className="community-card-heading">
                <strong>
                  {message.direction === "inbound"
                    ? "Received from"
                    : "Sent to"}{" "}
                  {message.party_id}
                </strong>
                <Badge>{message.status}</Badge>
              </div>
              <p className="message-body">{message.body}</p>
              <p className="community-meta">
                {message.channel} ·{" "}
                {new Date(message.created_wall).toLocaleTimeString()}
              </p>
              {message.error && (
                <p className="attention-label">{message.error}</p>
              )}
              {message.media_urls?.map((url, i) => {
                const safe = mediaLink(url);
                return safe ? (
                  <a
                    className="media-link"
                    key={i}
                    href={safe}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open photo {i + 1}
                  </a>
                ) : null;
              })}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
