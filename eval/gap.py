"""The remaining gap stays visible (feature 11, S5). Owner: D.

The console may show a segment as older than the truth (data is late or lost), never as
fresher. `hidden_s` measures, per segment, how many seconds the shore picture's seg_age
is younger than the worst true sample age. Anything above the slack hides part of the gap.
A segment no boat has ever visited must also exist in the shore picture.
"""

from eval.metrics import Coverage

# Shore ages come from heartbeats, which are periodic and arrive after a radio delay, while
# truth visits are credited every tick. The slack absorbs that timing, nothing else.
SLACK_S = 60


def hidden_s(shore_seg_age_s: dict[str, int], truth: Coverage) -> dict[str, int]:
    """Segment -> seconds the shore shows it younger than truth (0 if not younger). A segment
    missing from the shore picture is hidden completely: its whole true age."""
    result = {}
    for task, age_ms in sorted(truth.seg_age_ms.items()):
        true_s = age_ms // 1000
        shown = shore_seg_age_s.get(task)
        result[task] = true_s if shown is None else max(0, true_s - shown)
    return result


class GapAudit:
    """Accumulates the worst hiding per segment over a run."""

    def __init__(self, slack_s: int = SLACK_S):
        self.slack_s = slack_s
        self.worst: dict[str, tuple[int, int]] = {}  # task -> (hidden s, at sim s)

    def add(self, shore_seg_age_s: dict[str, int], truth: Coverage) -> None:
        for task, hidden in hidden_s(shore_seg_age_s, truth).items():
            if hidden > self.worst.get(task, (0, 0))[0]:
                self.worst[task] = (hidden, truth.t_ms // 1000)

    @property
    def violations(self) -> dict[str, tuple[int, int]]:
        return {k: v for k, v in sorted(self.worst.items()) if v[0] > self.slack_s}

    @property
    def max_hidden_s(self) -> int:
        return max((hidden for hidden, _ in self.worst.values()), default=0)

    def row(self) -> dict:
        return {
            "slack_s": self.slack_s,
            "max_hidden_s": self.max_hidden_s,
            "violations": {k: {"hidden_s": h, "at_s": at} for k, (h, at) in self.violations.items()},
            "ok": not self.violations,
        }
