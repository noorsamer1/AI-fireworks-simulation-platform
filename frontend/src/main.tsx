import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { setLocale } from "./lib/i18n";

setLocale("en");

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
