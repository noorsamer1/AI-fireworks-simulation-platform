import { create } from "zustand";

import { ShowWebSocket } from "../lib/ws";
import { useSidecarStore } from "./useSidecarStore";

export const SHOW_AGENT_ORDER = [
  "audio_analyst",
  "show_director",
  "effect_librarian",
  "choreographer",
  "effect_caster",
  "safety_auditor",
  "simulator",
  "critic",
  "exporter",
] as const;

export type ShowAgentId = (typeof SHOW_AGENT_ORDER)[number];

export type AgentStatus = "pending" | "running" | "completed" | "failed";

export type AgentRow = {
  status: AgentStatus;
  durationMs?: number;
  error?: string;
};

function isShowAgent(name: string): name is ShowAgentId {
  return (SHOW_AGENT_ORDER as readonly string[]).includes(name);
}

type ShowStore = {
  showId: string | null;
  agents: Record<ShowAgentId, AgentRow>;
  awaitingApproval: boolean;
  ws: ShowWebSocket | null;
  startShow: (showId: string) => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  approveShow: () => Promise<void>;
  requestRevision: (message: string) => Promise<void>;
  handleWSEvent: (data: unknown) => void;
};

function initialAgents(): Record<ShowAgentId, AgentRow> {
  return Object.fromEntries(
    SHOW_AGENT_ORDER.map((id) => [id, { status: "pending" as const }]),
  ) as Record<ShowAgentId, AgentRow>;
}

function applyAgentsCompleted(completed: unknown): Partial<Record<ShowAgentId, AgentRow>> {
  if (!Array.isArray(completed)) {
    return {};
  }
  const out: Partial<Record<ShowAgentId, AgentRow>> = {};
  for (const name of completed) {
    if (typeof name === "string" && isShowAgent(name)) {
      out[name] = { status: "completed" };
    }
  }
  return out;
}

export const useShowStore = create<ShowStore>((set, get) => ({
  showId: null,
  agents: initialAgents(),
  awaitingApproval: false,
  ws: null,

  startShow: (showId: string) => {
    set({
      showId,
      agents: initialAgents(),
      awaitingApproval: false,
    });
    get().connectWebSocket();
  },

  connectWebSocket: () => {
    const { showId } = get();
    const port = useSidecarStore.getState().port;
    if (!showId || port == null) {
      return;
    }
    get().disconnectWebSocket();
    const client = new ShowWebSocket(`127.0.0.1:${port}`, showId);
    client.connect((raw) => get().handleWSEvent(raw));
    set({ ws: client });
  },

  disconnectWebSocket: () => {
    const { ws } = get();
    ws?.disconnect();
    set({ ws: null });
  },

  approveShow: async () => {
    const { showId } = get();
    const port = useSidecarStore.getState().port;
    if (!showId || port == null) {
      return;
    }
    await fetch(`http://127.0.0.1:${port}/shows/${showId}/approve`, {
      method: "POST",
    });
  },

  requestRevision: async (message: string) => {
    const { showId } = get();
    const port = useSidecarStore.getState().port;
    if (!showId || port == null) {
      return;
    }
    await fetch(`http://127.0.0.1:${port}/shows/${showId}/revise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  },

  handleWSEvent: (raw: unknown) => {
    if (!raw || typeof raw !== "object") {
      return;
    }
    const data = raw as Record<string, unknown>;
    const type = data.event_type;
    if (typeof type !== "string") {
      return;
    }

    if (type === "ping") {
      return;
    }

    if (type === "state_sync") {
      const blob = data.data as Record<string, unknown> | undefined;
      const completed = blob?.agents_completed;
      const patch = applyAgentsCompleted(completed);
      set((s) => ({
        agents: { ...s.agents, ...patch },
        awaitingApproval: Boolean(blob?.awaiting_exporter),
      }));
      return;
    }

    if (type === "agent_started") {
      const name = data.agent_name as string | undefined;
      if (!name || !isShowAgent(name)) {
        return;
      }
      set((s) => ({
        agents: {
          ...s.agents,
          [name]: { ...s.agents[name], status: "running" },
        },
      }));
      return;
    }

    if (type === "agent_completed") {
      const name = data.agent_name as string | undefined;
      const duration = data.duration_ms;
      if (!name || !isShowAgent(name)) {
        return;
      }
      set((s) => ({
        agents: {
          ...s.agents,
          [name]: {
            status: "completed",
            durationMs: typeof duration === "number" ? duration : undefined,
          },
        },
      }));
      return;
    }

    if (type === "agent_failed") {
      const name = data.agent_name as string | undefined;
      const err = data.error;
      if (!name || !isShowAgent(name)) {
        return;
      }
      set((s) => ({
        agents: {
          ...s.agents,
          [name]: {
            status: "failed",
            error: typeof err === "string" ? err : String(err),
          },
        },
      }));
      return;
    }

    if (type === "awaiting_approval") {
      set({ awaitingApproval: true });
      return;
    }

    if (type === "export_started") {
      set({ awaitingApproval: false });
      set((s) => ({
        agents: {
          ...s.agents,
          exporter: { ...s.agents.exporter, status: "running" },
        },
      }));
      return;
    }

    if (type === "show_failed") {
      set({ awaitingApproval: false });
    }
  },
}));
