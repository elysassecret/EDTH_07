"""Revisit age per cable segment and cable km overdue (features 3 and 11). Owner: D.

Coverage comes only from physical sensor visits (`World.sample_visit_ms`): a boat must have
been within r_verify_m of a 100 m route sample. Owning or claiming a task counts for nothing
(S5). A sample never visited since t = 0 is aged from t = 0: the run starts cold, so no age
is invented for the time before it began.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coverage:
    t_ms: int
    target_ms: int
    overdue_m: int  # route metres whose newest visit is older than target_ms
    never_m: int  # route metres with no visit at all since t = 0
    worst_age_ms: int
    seg_age_ms: dict[str, int]  # task -> worst sample age
    seg_overdue_m: dict[str, int]
    seg_never_m: dict[str, int]

    @property
    def km_overdue(self) -> float:
        return self.overdue_m / 1000

    @property
    def km_never(self) -> float:
        return self.never_m / 1000

    def row(self) -> dict:
        """JSON-safe summary in seconds and km."""
        return {
            "t_s": self.t_ms // 1000,
            "target_s": self.target_ms // 1000,
            "km_overdue": self.km_overdue,
            "km_never_visited": self.km_never,
            "worst_age_s": self.worst_age_ms // 1000,
            "seg_age_s": {k: v // 1000 for k, v in sorted(self.seg_age_ms.items())},
            "seg_km_overdue": {k: v / 1000 for k, v in sorted(self.seg_overdue_m.items())},
            "seg_km_never_visited": {k: v / 1000 for k, v in sorted(self.seg_never_m.items())},
        }


def sample_ages(visit_ms: list[int | None], t_ms: int) -> list[int]:
    """Age of every sample at t_ms; never visited means aged from t = 0."""
    return [t_ms - (0 if v is None else v) for v in visit_ms]


def coverage(
    tasks: list[str], visit_ms: list[int | None], t_ms: int, target_ms: int, step_m: int
) -> Coverage:
    """`tasks[i]` is the task of sample i, aligned with `visit_ms`. Each sample stands for
    step_m of route; the short remainder at a segment end is not a sample and is not counted."""
    if len(tasks) != len(visit_ms):
        raise ValueError("tasks and visits must be aligned")
    seg_age: dict[str, int] = {}
    seg_over: dict[str, int] = {}
    seg_never: dict[str, int] = {}
    for task, visited, age in zip(tasks, visit_ms, sample_ages(visit_ms, t_ms), strict=True):
        seg_age[task] = max(seg_age.get(task, 0), age)
        seg_over[task] = seg_over.get(task, 0) + (step_m if age > target_ms else 0)
        seg_never[task] = seg_never.get(task, 0) + (step_m if visited is None else 0)
    return Coverage(
        t_ms=t_ms,
        target_ms=target_ms,
        overdue_m=sum(seg_over.values()),
        never_m=sum(seg_never.values()),
        worst_age_ms=max(seg_age.values(), default=0),
        seg_age_ms=seg_age,
        seg_overdue_m=seg_over,
        seg_never_m=seg_never,
    )


def world_coverage(sim, target_ms: int, step_m: int) -> Coverage:
    """Coverage of a running world.sim.World at its current tick."""
    tasks = [sample.task for sample in sim.scene.samples]
    return coverage(tasks, list(sim.sample_visit_ms), sim.t_ms, target_ms, step_m)


class Window:
    """Mean km overdue over regular checks inside [start_ms, end_ms]. One end-of-run number
    depends on where each boat happens to be at that instant; the mean shows the whole period."""

    def __init__(self, start_ms: int, end_ms: int):
        self.start_ms, self.end_ms = start_ms, end_ms
        self.total_m = 0
        self.count = 0

    def add(self, cov: Coverage) -> None:
        if self.start_ms <= cov.t_ms <= self.end_ms:
            self.total_m += cov.overdue_m
            self.count += 1

    @property
    def mean_km(self) -> float | None:
        return round(self.total_m / self.count / 1000, 3) if self.count else None
