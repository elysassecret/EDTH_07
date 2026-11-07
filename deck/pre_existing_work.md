# Pre-existing work (declare on one slide)

**[TO CONFIRM]** whether code written before Friday 19:00 counts. The Paris 2026 FAQ says only event work counts; Copenhagen's rule was not found. Ask the organisers.

Prepared before the event:
- `data/scene-coordinates.json`: box, public approximate cable lines (OSM, ODbL, © OpenStreetMap contributors), lane centreline measured from one AIS day, candidate stations.
- `data/ais-clip-box.csv`: one day (3 Nov 2026) of Danish Maritime Authority AIS inside the box, anonymised (salted hashes, no names, 25 m length bands). Kept inside the team, gitignored.
- Research notes and the build plan.
- Franco's reference branch `franko-initial-fable`, a separate simulator written from the public brief. Its code is not in this product, but `eval/`, tests and these documents were ported from it during the event, and some issues to teammates point to it.

Everything else in this repository is to be declared per the rule the organisers give. If pre-event code is disallowed, the honest statement is: "the architecture was drafted before the event from the public brief; at the event we built, integrated, measured, tested and recorded." **[Check against `git log` before using this sentence.]**
