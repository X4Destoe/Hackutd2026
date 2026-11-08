import { createServer, type Server } from "node:http";
import { pathToFileURL } from "node:url";
import { Spectrum } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";
export type SendInput = { phone: string; text: string; media_url?: string };
export type Sender = (input: SendInput) => Promise<{ message_id: string }>;
const E164 = /^\+[1-9]\d{7,14}$/;
export function allowedPhones(
  value = process.env.DEMO_PHONES ?? "",
): Set<string> {
  return new Set(
    value
      .split(",")
      .map((v) => v.trim().split(":")[0])
      .filter((v) => E164.test(v)),
  );
}
export function validateInput(value: unknown): SendInput {
  if (!value || typeof value !== "object")
    throw new Error("Expected JSON object");
  const v = value as Record<string, unknown>;
  if (typeof v.phone !== "string" || !E164.test(v.phone))
    throw new Error("phone must be international E.164");
  if (typeof v.text !== "string" || !v.text.trim() || v.text.length > 2000)
    throw new Error("text must contain 1–2000 characters");
  if (v.media_url !== undefined)
    throw new Error(
      "Outbound media is not enabled in this spike; inbound photo replies are supported by the webhook",
    );
  return { phone: v.phone, text: v.text };
}
export function createSpectrumSender(): Sender {
  const connect = (projectId: string, projectSecret: string) =>
    Spectrum({ projectId, projectSecret, providers: [imessage.config()] });
  let runtime: ReturnType<typeof connect> | undefined;
  return async ({ phone, text }) => {
    const projectId = process.env.SPECTRUM_PROJECT_ID;
    const projectSecret = process.env.SPECTRUM_PROJECT_SECRET;
    if (!projectId || !projectSecret)
      throw new Error("Missing Spectrum configuration");
    runtime ??= connect(projectId, projectSecret);
    const app = await runtime;
    const space = await imessage(app).space.create(
      phone,
      process.env.SPECTRUM_SENDER
        ? { phone: process.env.SPECTRUM_SENDER }
        : undefined,
    );
    const message = await space.send(text);
    if (!message?.id) throw new Error("No message acknowledgement");
    return { message_id: message.id };
  };
}
/** Loopback-only spike. It never retries a real send automatically. */
export function createBridge(
  sender: Sender,
  recipients: Set<string>,
  configured: boolean,
  timeoutMs = 15000,
): Server {
  let busy = false;
  return createServer(async (req, res) => {
    const reply = (status: number, body: unknown) => {
      if (!res.writableEnded) {
        res.writeHead(status, { "Content-Type": "application/json" });
        res.end(JSON.stringify(body));
      }
    };
    if (req.method === "GET" && req.url === "/health")
      return reply(200, {
        ok: true,
        configured,
        recipient_count: recipients.size,
      });
    if (req.method !== "POST" || req.url !== "/send")
      return reply(404, { error: "Not found" });
    if (
      req.headers.origin ||
      !req.headers["content-type"]?.startsWith("application/json")
    )
      return reply(415, { error: "Use local application/json requests" });
    let raw = "";
    try {
      for await (const chunk of req) {
        raw += chunk.toString();
        if (Buffer.byteLength(raw) > 16384)
          return reply(413, { error: "Request too large" });
      }
      let input: SendInput;
      try {
        input = validateInput(JSON.parse(raw));
      } catch {
        return reply(400, {
          error: "Invalid phone/text; outbound media is not supported",
        });
      }
      if (!configured)
        return reply(503, { error: "Spectrum credentials are not configured" });
      if (!recipients.has(input.phone))
        return reply(403, { error: "Recipient is not listed in DEMO_PHONES" });
      if (busy)
        return reply(409, {
          error: "Another send is in progress; do not retry automatically",
        });
      busy = true;
      const timer = setTimeout(
        () =>
          reply(504, {
            error: "Send outcome unknown; check provider before retrying",
          }),
        timeoutMs,
      );
      try {
        const result = await sender(input);
        reply(200, { status: "accepted", ...result });
      } catch {
        reply(502, {
          error:
            "Spectrum send failed; inspect provider status before retrying",
        });
      } finally {
        clearTimeout(timer);
        busy = false;
      }
    } catch {
      reply(400, { error: "Could not read request" });
    }
  });
}
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  const configured = Boolean(
    process.env.SPECTRUM_PROJECT_ID && process.env.SPECTRUM_PROJECT_SECRET,
  );
  const server = createBridge(
    createSpectrumSender(),
    allowedPhones(),
    configured,
  );
  server.requestTimeout = 20000;
  server.listen(
    Number(process.env.PHOTON_BRIDGE_PORT ?? 8787),
    "127.0.0.1",
    () =>
      console.log(
        "Photon bridge listening on loopback; real send requires credentials and DEMO_PHONES",
      ),
  );
}
