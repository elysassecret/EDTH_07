// Owner: C. "Escalate: report onward" on a selected contact. The watch officer reads a
// radio-ready report built only from delivered data, may add a note, and records the
// escalation. The server keeps the exact text in the evidence log. The console never labels a
// contact a threat; this is the officer's decision and is shown as such.
import { useState } from "react";
import { Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { canOperate } from "../console-model";
import { escalationOf, reportText } from "../escalate";
import { hhmm } from "../format";
import { useStore } from "../store";
import { t0Of, type Contact, type Snapshot } from "../types";

export function EscalateControl({ contact, snap }: { contact: Contact; snap: Snapshot }) {
  const conn = useStore((s) => s.conn);
  const channel = useStore((s) => s.channel);
  const send = useStore((s) => s.send);
  const ack = useStore((s) => s.lastAck);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [note, setNote] = useState("");
  const [sent, setSent] = useState(false);
  const done = escalationOf(snap, contact.id);
  const locked = !canOperate(conn, channel);
  const failed = sent && ack?.cmd === "escalate" && ack.ok === false ? ack.error : null;

  return (
    <div className="space-y-2">
      {done && (
        <Badge variant="secondary">
          ESCALATED BY WATCH OFFICER {hhmm(t0Of(snap), done.t)}
        </Badge>
      )}
      <Button
        variant="outline"
        size="sm"
        disabled={locked}
        onClick={() => {
          setText(reportText(contact, snap, t0Of(snap)));
          setNote("");
          setSent(false);
          setOpen(true);
        }}
      >
        <Send />
        {done ? "Escalate again…" : "Escalate: report onward…"}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85dvh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Report {contact.track} onward</DialogTitle>
            <DialogDescription>
              Your decision as watch officer, for the Navy or the rescue centre (JRCC). The
              boats only give a cue for a look; they do not judge intent.
            </DialogDescription>
          </DialogHeader>
          <label className="block space-y-1 text-sm">
            <span className="font-medium">Report (from delivered data only)</span>
            <textarea
              readOnly
              aria-label="Report text"
              className="h-40 w-full rounded-md border bg-muted/30 p-2 font-mono text-xs"
              value={text}
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-medium">Your note (optional)</span>
            <input
              aria-label="Officer note"
              className="w-full rounded-md border bg-background p-2"
              maxLength={300}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <p className="text-sm text-muted-foreground">
            Recording does not transmit anything to the Navy or JRCC: this console has no
            outside link. Copy the text into your radio or phone log. The record goes into the
            tamper-checked evidence log.
          </p>
          {sent && !failed && done && <p role="status">Recorded at {hhmm(t0Of(snap), done.t)}.</p>}
          {failed && <p role="alert" className="text-destructive">Not recorded: {failed}</p>}
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Close</Button>
            </DialogClose>
            <Button variant="outline" onClick={() => void navigator.clipboard?.writeText(text)}>
              Copy text
            </Button>
            <Button
              disabled={locked || (sent && !failed)}
              onClick={() => {
                setSent(send({ cmd: "escalate", id: contact.id, text, note }));
              }}
            >
              Record escalation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
