import { useCallback, useEffect, useState } from "react";
import { getHealth } from "./lib/api";
import { isTauri } from "./lib/isTauri";
import { setLocale, t } from "./lib/i18n";
import { useSidecarStore } from "./stores/useSidecarStore";
import AgentChatPanel from "./components/AgentChatPanel";
import { SongDropzone } from "./components/ProjectWorkspace/SongDropzone";
import "./App.css";

function App() {
  const [status, setStatus] = useState(t("sidecar.checking"));
  const [projectId, setProjectId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const checkHealth = async () => {
      if (!isTauri() && !import.meta.env.VITE_SIDECAR_PORT) {
        if (!cancelled) {
          setStatus(t("sidecar.browserNeedDesktop"));
        }
        return;
      }

      const maxAttempts = 30;

      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        try {
          await useSidecarStore.getState().init();
          const health = await getHealth();
          if (!cancelled) {
            setStatus(
              health.status === "ok" ? t("sidecar.ok") : t("sidecar.unhealthy"),
            );
          }
          return;
        } catch {
          if (attempt < maxAttempts - 1) {
            await new Promise((resolve) => setTimeout(resolve, 1000));
          }
        }
      }

      if (!cancelled) {
        setStatus(t("sidecar.unreachable"));
      }
    };

    void checkHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  const createProject = useCallback(async () => {
    const port = useSidecarStore.getState().port;
    if (port == null) {
      return;
    }
    const res = await fetch(`http://127.0.0.1:${port}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Workspace" }),
    });
    if (!res.ok) {
      return;
    }
    const body = (await res.json()) as { id: string };
    setProjectId(body.id);
  }, []);

  return (
    <main className="container">
      <h1>{t("app.title")}</h1>
      <p>{status}</p>
      <div className="workspace-toolbar">
        <button type="button" onClick={() => setLocale("en")}>
          {t("workspace.lang_en")}
        </button>
        <button type="button" onClick={() => setLocale("ar")}>
          {t("workspace.lang_ar")}
        </button>
        <button type="button" onClick={() => void createProject()}>
          {t("workspace.create_project")}
        </button>
        {projectId ? (
          <span className="workspace-project-id">
            {t("workspace.project_label")}: {projectId}
          </span>
        ) : null}
      </div>
      {projectId ? <SongDropzone projectId={projectId} /> : null}
      <AgentChatPanel />
    </main>
  );
}

export default App;
