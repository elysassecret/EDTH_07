// Owner: C. Entry: start the feed connection, render the app.
// No <StrictMode>: its dev-only double mount creates and removes the MapLibre map at once;
// one map instance keeps dev behaviour the same as the built console.
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { connect } from "./store";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "./styles.css";

document.documentElement.classList.add("dark");

connect();
createRoot(document.getElementById("root")!).render(<App />);
