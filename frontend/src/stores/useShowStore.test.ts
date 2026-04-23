import { beforeEach, describe, expect, it, vi } from "vitest";

import { setLocale } from "../lib/i18n";
import {
  SHOW_AGENT_ORDER,
  useShowStore,
  type AgentRow,
  type ShowAgentId,
} from "./useShowStore";

function blankAgents(): Record<ShowAgentId, AgentRow> {
  return Object.fromEntries(
    SHOW_AGENT_ORDER.map((id) => [id, { status: "pending" as const }]),
  ) as Record<ShowAgentId, AgentRow>;
}

vi.mock("../lib/ws", () => ({
  ShowWebSocket: vi.fn().mockImplementation(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  })),
}));

describe("useShowStore", () => {
  beforeEach(() => {
    setLocale("en");
    useShowStore.getState().disconnectWebSocket();
    useShowStore.setState({
      showId: null,
      agents: blankAgents(),
      awaitingApproval: false,
      ws: null,
    });
  });

  it("updates agent rows through a typical event sequence", () => {
    const { handleWSEvent } = useShowStore.getState();
    handleWSEvent({ event_type: "agent_started", agent_name: "audio_analyst" });
    expect(useShowStore.getState().agents.audio_analyst.status).toBe("running");

    handleWSEvent({
      event_type: "agent_completed",
      agent_name: "audio_analyst",
      duration_ms: 120,
    });
    expect(useShowStore.getState().agents.audio_analyst.status).toBe("completed");
    expect(useShowStore.getState().agents.audio_analyst.durationMs).toBe(120);

    handleWSEvent({ event_type: "agent_started", agent_name: "show_director" });
    expect(useShowStore.getState().agents.show_director.status).toBe("running");

    handleWSEvent({ event_type: "awaiting_approval" });
    expect(useShowStore.getState().awaitingApproval).toBe(true);
  });
});
