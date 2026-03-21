import type { HookHandler } from "openclaw/hooks";

const handler: HookHandler = async (event) => {
  if (event.type !== "gateway" || event.action !== "startup") return;

  // Register that the agent now has the screen.context tool (via OpenWeruh daemon)
  event.messages.push(
    "[OpenWeruh] Screen context layer active. " +
    "Tool screen.context is effectively available for visual analysis."
  );
};

export default handler;