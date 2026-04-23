import { useCallback, useRef, useState } from "react";

import { t } from "../../lib/i18n";
import { useSidecarStore } from "../../stores/useSidecarStore";
import { useShowStore } from "../../stores/useShowStore";
import styles from "./SongDropzone.module.css";

const ACCEPT = [".wav", ".mp3", ".flac"];

type Props = {
  projectId: string;
};

function extOk(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPT.some((e) => lower.endsWith(e));
}

export function SongDropzone({ projectId }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);

  const uploadFile = useCallback(
    (file: File) => {
      setError(null);
      setProgress(0);
      if (!extOk(file.name)) {
        setError(t("songdrop.bad_type"));
        setProgress(null);
        return;
      }
      const port = useSidecarStore.getState().port;
      if (port == null) {
        setError(t("songdrop.no_port"));
        setProgress(null);
        return;
      }
      const url = `http://127.0.0.1:${port}/shows/`;
      const fd = new FormData();
      fd.append("project_id", projectId);
      fd.append("song", file);
      fd.append("language", document.documentElement.lang === "ar" ? "ar" : "en");

      const xhr = new XMLHttpRequest();
      xhr.open("POST", url);
      xhr.upload.onprogress = (ev) => {
        if (ev.lengthComputable) {
          setProgress(Math.round((ev.loaded / ev.total) * 100));
        }
      };
      xhr.onload = () => {
        setProgress(null);
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const body = JSON.parse(xhr.responseText) as { show_id?: string };
            if (body.show_id) {
              useShowStore.getState().startShow(body.show_id);
            }
          } catch {
            setError(t("songdrop.bad_response"));
          }
        } else {
          setError(t("songdrop.upload_failed"));
        }
      };
      xhr.onerror = () => {
        setProgress(null);
        setError(t("songdrop.network_error"));
      };
      xhr.send(fd);
    },
    [projectId],
  );

  const onPick = () => inputRef.current?.click();

  return (
    <div className={styles.wrap} dir="auto">
      <div
        role="button"
        tabIndex={0}
        className={`${styles.zone} ${drag ? styles.zoneDrag : ""}`}
        onClick={onPick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onPick();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files[0];
          if (f) {
            uploadFile(f);
          }
        }}
      >
        <p className={styles.hint}>{t("songdrop.hint")}</p>
        <button
          type="button"
          className={styles.pickBtn}
          onClick={(e) => {
            e.stopPropagation();
            onPick();
          }}
        >
          {t("songdrop.browse")}
        </button>
      </div>
      <input
        ref={inputRef}
        className={styles.hiddenInput}
        type="file"
        accept={ACCEPT.join(",")}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) {
            uploadFile(f);
          }
          e.target.value = "";
        }}
      />
      {progress != null ? (
        <div className={styles.progress} aria-label={t("songdrop.progress_label")}>
          <div className={styles.progressBar} style={{ width: `${progress}%` }} />
        </div>
      ) : null}
      {error ? <div className={styles.err}>{error}</div> : null}
    </div>
  );
}
