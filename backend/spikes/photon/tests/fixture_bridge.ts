// Test-only transport fixture: no credentials or SDK sends.
import { createBridge } from "../bridge.js";
import type { AddressInfo } from "node:net";
const server = createBridge(
  async () => ({ message_id: "fixture-message" }),
  new Set(["+12145550100"]),
  true,
);
server.listen(0, "127.0.0.1", () =>
  console.log((server.address() as AddressInfo).port),
);
