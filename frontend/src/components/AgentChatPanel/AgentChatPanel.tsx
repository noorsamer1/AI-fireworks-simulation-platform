import { useShowStore, SHOW_AGENT_ORDER, type ShowAgentId } from "../../stores/useShowStore";
import { t } from "../../lib/i18n";
import styles from "./AgentChatPanel.module.css";

function statusLabel(status: string): string {
  if (status === "pending") {
    return t("status.pending");
  }
  if (status === "running") {
    return t("status.running");
  }
  if (status === "completed") {
    return t("status.completed");
  }
  if (status === "failed") {
    return t("status.failed");
  }
  return status;
}

function iconFor(status: string): string {
  if (status === "completed") {
    return "✓";
  }
  if (status === "failed") {
    return "✕";
  }
  if (status === "running") {
    return "›";
  }
  return "○";
}

function agentTitle(id: ShowAgentId): string {
  return t(`agent.${id}`);
}

export default function AgentChatPanel() {
  const agents = useShowStore((s) => s.agents);
  const awaiting = useShowStore((s) => s.awaitingApproval);
  const approveShow = useShowStore((s) => s.approveShow);
  const requestRevision = useShowStore((s) => s.requestRevision);

  return (
    <section className={styles.root} dir="auto">
      <h2 className={styles.title}>{t("panel.agents_title")}</h2>
      <ul className={styles.list}>
        {SHOW_AGENT_ORDER.map((id) => {
          const row = agents[id];
          const running = row?.status === "running";
          return (
            <li
              key={id}
              className={`${styles.row} ${running ? styles.rowRunning : ""}`}
            >
              <span className={styles.icon} aria-hidden>
                {iconFor(row?.status ?? "pending")}
              </span>
              <div className={styles.body}>
                <div className={styles.nameRow}>
                  <strong>{agentTitle(id)}</strong>
                  <span className={styles.badge}>{statusLabel(row?.status ?? "pending")}</span>
                  {row?.durationMs != null ? (
                    <span className={styles.duration}>{row.durationMs} ms</span>
                  ) : null}
                </div>
                {row?.status === "failed" && row.error ? (
                  <div className={styles.err}>{row.error}</div>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
      {awaiting ? (
        <div className={styles.actions}>
          <button type="button" className={styles.approveBtn} onClick={() => void approveShow()}>
            {t("panel.approve")}
          </button>
          <form
            className={styles.reviseRow}
            onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              const msg = String(fd.get("revision") ?? "").trim();
              if (!msg) {
                return;
              }
              void requestRevision(msg);
              e.currentTarget.reset();
            }}
          >
            <input
              className={styles.input}
              name="revision"
              placeholder={t("panel.revise_placeholder")}
            />
            <button type="submit" className={styles.reviseBtn}>
              {t("panel.revise_submit")}
            </button>
          </form>
        </div>
      ) : null}
    </section>
  );
}
