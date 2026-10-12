import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App.jsx";
import "./index.css";

// StrictMode on purpose: it double-invokes effects in development, which is how a request fired
// from an effect without a guard shows up as two requests rather than as a mystery later.
createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
