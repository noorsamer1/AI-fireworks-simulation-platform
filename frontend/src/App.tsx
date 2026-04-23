import { useEffect, useState } from "react";
import { getHealth } from "./lib/api";
import { t } from "./lib/i18n";
import { useSidecarStore } from "./stores/useSidecarStore";
import "./App.css";

function App() {
  const [status, setStatus] = useState(t("sidecar.checking"));

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await useSidecarStore.getState().init();
        const health = await getHealth();
        setStatus(
          health.status === "ok" ? t("sidecar.ok") : t("sidecar.unhealthy"),
        );
      } catch {
        setStatus(t("sidecar.unreachable"));
      }
    };

    void checkHealth();
  }, []);

  return (
    <main className="container">
      <h1>{t("app.title")}</h1>
      <p>{status}</p>
    </main>
  );
}

export default App;
