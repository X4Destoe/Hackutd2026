import test from "node:test";
import assert from "node:assert/strict";
import { once } from "node:events";
import type { AddressInfo } from "node:net";
import { createBridge, allowedPhones, validateInput } from "../bridge.js";
async function fixture(
  sender: Parameters<typeof createBridge>[0],
  configured = true,
  timeout = 1000,
) {
  const server = createBridge(
    sender,
    new Set(["+12145550100"]),
    configured,
    timeout,
  );
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const url = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  return {
    server,
    url,
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}
const request = (
  url: string,
  body: unknown,
  headers: Record<string, string> = {},
) =>
  fetch(url + "/send", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
test("only explicitly mapped international demo numbers", () => {
  assert.deepEqual(
    [...allowedPhones("+12145550100:TECH-HOU-01,invalid,+14695550100:TEN-001")],
    ["+12145550100", "+14695550100"],
  );
  assert.throws(() => validateInput({ phone: "555", text: "hello" }));
  assert.throws(() => validateInput({ phone: "+12145550100", text: "" }));
  assert.throws(() =>
    validateInput({
      phone: "+12145550100",
      text: "hello",
      media_url: "https://example.com/photo",
    }),
  );
});
test("SDK injected sender receives Python-compatible payload once", async () => {
  const seen: unknown[] = [];
  const f = await fixture(async (input) => {
    seen.push(input);
    return { message_id: "message-1" };
  });
  try {
    const r = await request(f.url, {
      phone: "+12145550100",
      text: "Operation Storm test",
    });
    assert.equal(r.status, 200);
    assert.deepEqual(await r.json(), {
      status: "accepted",
      message_id: "message-1",
    });
    assert.equal(seen.length, 1);
    assert.equal(
      (await request(f.url, { phone: "+12145550199", text: "blocked" })).status,
      403,
    );
    assert.equal(seen.length, 1);
  } finally {
    await f.close();
  }
});
test("unconfigured server is healthy but does not send", async () => {
  const f = await fixture(async () => {
    throw Error("must not call");
  }, false);
  try {
    assert.equal(
      (await request(f.url, { phone: "+12145550100", text: "hello" })).status,
      503,
    );
    assert.equal((await fetch(f.url + "/health")).status, 200);
  } finally {
    await f.close();
  }
});
test("browser origin and invalid bodies are rejected", async () => {
  const f = await fixture(async () => ({ message_id: "x" }));
  try {
    assert.equal(
      (
        await request(
          f.url,
          { phone: "+12145550100", text: "hello" },
          { Origin: "https://example.com" },
        )
      ).status,
      415,
    );
    assert.equal(
      (await request(f.url, { phone: "bad", text: "hello" })).status,
      400,
    );
  } finally {
    await f.close();
  }
});
test("timeout reports unknown outcome and keeps in-flight send bounded", async () => {
  let finish!: (x: { message_id: string }) => void;
  const pending = new Promise<{ message_id: string }>(
    (resolve) => (finish = resolve),
  );
  const f = await fixture(() => pending, true, 20);
  try {
    assert.equal(
      (await request(f.url, { phone: "+12145550100", text: "hello" })).status,
      504,
    );
    assert.equal(
      (await request(f.url, { phone: "+12145550100", text: "hello" })).status,
      409,
    );
    finish({ message_id: "late" });
  } finally {
    finish({ message_id: "late" });
    await f.close();
  }
});
