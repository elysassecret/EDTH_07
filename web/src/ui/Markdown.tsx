// Owner: C. #88 item 7: a small Markdown renderer for the bundled guides (deck/OPERATOR_GUIDE.md,
// world/MODEL.md, agent/RULES.md). Builds React elements only, never raw HTML, and needs no
// network or extra package. Covers what those files use: headings, paragraphs, lists, tables,
// **bold** and `code`.
import type { ReactNode } from "react";

function inline(text: string, key: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={`${key}-${i}`}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={`${key}-${i}`} className="font-mono">{part.slice(1, -1)}</code>;
    return part;
  });
}

const cells = (row: string) => row.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

export function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const out: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const k = `l${i}`;
    if (!line.trim()) { i++; continue; }
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      const cls = h[1].length === 1 ? "text-lg font-semibold" : "mt-2 font-semibold";
      out.push(<p key={k} className={cls} role="heading" aria-level={h[1].length + 1}>{inline(h[2], k)}</p>);
      i++;
      continue;
    }
    if (line.trim().startsWith("|") && i + 1 < lines.length && /^\s*\|?\s*:?-{3}/.test(lines[i + 1])) {
      const head = cells(line);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(cells(lines[i++]));
      out.push(
        <table key={k} className="w-full text-left text-sm">
          <thead><tr className="border-b text-muted-foreground">{head.map((c, j) => <th key={j} className="py-1 pr-3 font-medium">{inline(c, `${k}h${j}`)}</th>)}</tr></thead>
          <tbody>{rows.map((r, n) => <tr key={n} className="border-b last:border-0">{r.map((c, j) => <td key={j} className="py-1 pr-3 align-top">{inline(c, `${k}r${n}c${j}`)}</td>)}</tr>)}</tbody>
        </table>,
      );
      continue;
    }
    const li = /^\s*(?:[-*]|\d+\.)\s+/;
    if (li.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items: string[] = [];
      while (i < lines.length && li.test(lines[i])) items.push(lines[i++].replace(li, ""));
      const List = ordered ? "ol" : "ul";
      out.push(<List key={k} className={`${ordered ? "list-decimal" : "list-disc"} space-y-1 pl-5`}>{items.map((t, n) => <li key={n}>{inline(t, `${k}i${n}`)}</li>)}</List>);
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^#{1,4}\s/.test(lines[i]) && !lines[i].trim().startsWith("|") && !li.test(lines[i])) para.push(lines[i++]);
    out.push(<p key={k}>{inline(para.join(" "), k)}</p>);
  }
  return <div className="space-y-2 text-sm">{out}</div>;
}

// Bundled at build time; a file that does not exist yet is simply left out (glob finds nothing).
const files = import.meta.glob(["../../../deck/OPERATOR_GUIDE.md", "../../../world/MODEL.md", "../../../agent/RULES.md"],
  { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const pick = (end: string) => Object.entries(files).find(([p]) => p.endsWith(end))?.[1] ?? null;
export const GUIDE = { operator: pick("deck/OPERATOR_GUIDE.md"), model: pick("world/MODEL.md"), rules: pick("agent/RULES.md") };
