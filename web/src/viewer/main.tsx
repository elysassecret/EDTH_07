import { createRoot } from "react-dom/client";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "../styles.css";
import "./viewer.css";
import { ViewerApp } from "./ViewerApp";

createRoot(document.getElementById("root")!).render(<ViewerApp />);
