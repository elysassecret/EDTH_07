# Competitors and prior art: USV swarm coordination and subsea-cable watch

Research date: 6 November 2026. Evidence tags used below: **[FIELDED]** in real operational use; **[DEMO]** one-off trial or exercise; **[VENDOR]** company claim with no independent check; **[RESEARCH]** paper or simulation; **[WEAK]** single low-quality or secondary source.

Limits of this research: NATO ACT pages and Forbes returned 403, two Naval News pages returned 503, USNI returned 403, and the National Defense page came back empty, so those are cited only from search snippets where noted. The web search budget ran out before Global Fishing Watch could be checked. "Not found" below means not found in public sources, not "does not exist". Classified or unpublished systems may do more.

## What systems already fuse AIS and flag risk to subsea cables or the shadow fleet, and do any task uncrewed boats?

### Takeaway
Spotting risky ships near cables is fielded and crowded: state systems (Nordic Warden), commercial platforms (Windward) and cable-owner AIS services (Vesper, NKT) all do it. No source reviewed shows a cable-risk alert tasking an uncrewed boat. The "tasking" on offer is satellite imagery, so the last mile from alert to boat is the open part.

### Cited Findings
**State systems**
- **[FIELDED] Nordic Warden (JEF, UK-led).** Activated after the Estlink 2 damage; it uses AI on data including AIS to assess the risk of each vessel entering areas of interest, and was integrated into CTF Baltic's operations — [Atlantic Council, 26 Nov 2025](https://www.atlanticcouncil.org/in-depth-research-reports/issue-brief/how-the-baltic-sea-nations-have-tackled-suspicious-cable-cuts/).
- Nordic Warden monitors 22 areas of interest, including parts of the English Channel, North Sea, Kattegat and Baltic, run from Northwood — [Yahoo news report, Jan 2025, via search snippet](https://www.yahoo.com/news/british-led-force-ai-tracking-130419594.html). Vessels identified as shadow fleet are registered so they can be watched closely — [USNI News, 7 Jan 2025, via search snippet](https://news.usni.org/2025/01/07/uk-to-lead-joint-expeditionary-force-nato-effort-to-track-russian-shadow-fleet). It was trialled in summer 2024 and during Exercise Joint Protector — [Naval News, via search snippet](https://www.navalnews.com/?p=66714). No public source reviewed mentions it tasking uncrewed boats.
- **[FIELDED] Baltic Sentry.** Announced January 2025 as a component of CTF Baltic (Rostock, set up October 2024, about 90 naval officers), not a new organisation. It adds vessels, patrol aircraft and staff — [Atlantic Council](https://www.atlanticcouncil.org/in-depth-research-reports/issue-brief/how-the-baltic-sea-nations-have-tackled-suspicious-cable-cuts/).
- The same brief reports no suspicious Baltic undersea incidents since January 2025 and quotes CTF Baltic calling this a sign deterrence works, while noting it cannot be verified — [Atlantic Council](https://www.atlanticcouncil.org/in-depth-research-reports/issue-brief/how-the-baltic-sea-nations-have-tackled-suspicious-cable-cuts/). Five weeks later Finland seized the cargo ship Fitburg over damage to an Elisa cable, on 31 December 2025 — [The Record](https://therecord.media/finland-arrests-crew-ship-suspected-cable-break).

**Commercial platforms (all vendor pages, no independent evaluation found)**
- **[VENDOR] Windward.** Users draw zones around cable routes; alerts fire when risky vessels enter or suspicious activity occurs; each alert carries identity, ownership, behaviour, proximity and a risk rationale. Satellite EO, SAR and RF track vessels after AIS goes off. Users can "Task new imagery of approaching vessels". Alerts "can be integrated into command-and-control systems". Events are logged with time-stamped timelines for replay and investigation records — [Windward CMIP page](https://windward.ai/solutions/maritime-infrastructure/).
- Windward's cable and TSO pages do not mention predicted crossings, ETA prediction, a dedicated anchor-drag detector, or tasking of drones, USVs or crews. The only tasking is satellite imagery — [Windward CMIP page](https://windward.ai/solutions/maritime-infrastructure/); [Windward TSO page](https://windward.ai/industries/transmission-system-operators/).
- Windward's September 2026 case list includes spoofed AIS over the Luzon Strait, two sanctioned tankers holding about 40 and 45 hours over North Sea pipelines without going dark, a Russian trawler over five transatlantic cables with no AIS gaps, and Russian-flagged tugs in the Kattegat and Skagerrak confirmed by EO and SAR — [Windward blog, Oct 2026](https://windward.ai/blog/vessels-loiter-over-subsea-cables-and-pipelines-across-five-theaters/).
- Windward counted 34,081 vessel activities near global undersea cables in Q2 2026 — [Windward Q2 2026 report](https://windward.ai/knowledge-base/q2-2026-undersea-cables-risk-report/).
- HawkEye 360 and Windward partner so a customer can check a reported AIS position and keep tracking after a vessel goes dark — [Windward news, undated](https://windward.ai/news/hawkeye-360-and-windward-partner-to-provide-deeper-insights-and-better-visibility-on-vessel-behavior).
- **[FIELDED, free tool] Skylight (Allen Institute for AI).** Lists rendezvous, dark rendezvous, entry and speed-range events plus satellite radar detection; dark rendezvous is a plausible transshipment where only one vessel uses AIS, and it also catches harmless movements, so a flag is not proof — [Skylight docs](https://skylight.helpjuice.com/en_US/dark-rendezvous). It can automatically trigger satellite images on certain behaviours and offers an API — [Spire customer spotlight](https://spire.com/?p=7140). Nothing found on cables or boats.
- **Kpler.** A report used 60 days of AIS near Svalbard to flag loitering and fishing anomalies near cables — [Distill Intelligence summary, WEAK](https://www.distillintelligence.com/news/kpler). No cable alert product confirmed.
- **Spire.** Says AIS can flag vessels on collision courses with offshore assets so operators can warn or notify authorities — [Spire blog, VENDOR](https://spire.com/?p=15831). No cable product confirmed.
- **Saildrone and Palantir.** The partnership (13 March 2025) is framed around AI-powered tasking of autonomous assets, using Palantir's cloud — [Naval News, via search snippet](https://www.navalnews.com/naval-news/2025/03/saildrone-and-palantir-announce-strategic-partnership-to-advance-ai-powered-maritime-intelligence/). This is the closest public statement of "intelligence platform tasks USVs"; no cable-specific tasking described.

**Cable-owner AIS watch services (these are old and ordinary)**
- **[FIELDED] Vesper Marine WatchMate/Guardian at NYPA, Long Island Sound.** Virtual AIS markers on the cable zone; when a ship appears to be anchoring in the zone an alert goes to NYPA and an AIS text warning goes to the ship — [MarineLink](https://marinelink.com/news/underwater-protect-marine412671); [NAWindpower](https://nawindpower.com/nypa-deploys-system-to-avoid-anchor-strikes-to-underwater-transmission-cables). The same product is sold for Thai cables — [Professional Mariner](https://professionalmariner.com/vesper-marines-guardian-to-protect-subsea-cables-in-thailand/).
- **[FIELDED] NKT AIS monitoring (2021).** Satellite and VHF AIS, protection zones built from a risk study, rules for fishing and anchoring, alarm on rule break — [offshoreWIND.biz, 9 Sep 2021](https://www.offshorewind.biz/2021/09/09/using-ais-monitoring-to-reduce-the-risk-of-subsea-cable-failures-caused-by-external-factors). The article does not cover crossing prediction or guard vessels.
- Another provider flags speed over ground, sudden slowing and veering off course — [Subsea Asset Protection](https://sap.imaniprima.co.id/).

### Inferences
- "AIS plus a geofence plus abnormal behaviour" will not impress an expert: it has been sold for years. "Predicted crossing" looks less advertised on the pages read, but it is a simple extension of AIS course and speed, and a vendor can add it easily, so treat it as a feature, not a breakthrough.
- The gap worth claiming is the last mile: turning any alert into one boat's job, inside a small fleet, without breaking the patrol. Vendors stop at an alert, a satellite image or a C2 feed.
- A trap: "AIS dark" is the challenge's scenario, but several cases on record stayed on AIS. A cue that only fires on dark ships would miss them. Include "AIS on, behaving oddly".

### Gaps
- Global Fishing Watch was not checked (search budget used up).
- No 2026 status update on Nordic Warden found; all sources date from January 2025.
- Cannot rule out that Windward or others offer crossing prediction outside the pages read.

## What cable-side sensing exists, how fast can an alarm localise a fault, and can it feed a fleet?

### Takeaway
Fibre sensing (DAS) is moving from pilot to service, with Elisa's Baltic work the most relevant, but under 1% of cables have sensing, by one vendor's count. Best published field localisation is tens of metres; an electrical fault fix is roughly 1% of cable length. Alarms mostly fire at or seconds before impact, so they are a "go now, who was here?" cue, not an early warning. No source shows one feeding uncrewed boats.

### Cited Findings
**What exists**
- **[FIELDED/near-service] Elisa, Finland.** Finished Baltic DAS testing with the Finnish navy and border guard and is turning it into an automated service to warn authorities and infrastructure owners, for example of a ship dragging its anchor. No range or accuracy published — [Light Reading, 5 Jun 2026](https://www.lightreading.com/security/elisa-gives-its-subsea-cable-ears).
- **[VENDOR] Fibersense.** Says fewer than 1% of submarine cables have sensing, claims five-metre resolution across thousands of kilometres and false positives of 1 to 3% for threat classification — [TeleGeography, 2 Oct 2025](https://resources.telegeography.com/protecting-internet-infrastructure-submarine-cable-sensing). The range claim sits oddly with the single-span limit below.
- **[DEMO] Indeximate with STFC Hartree.** ML on DAS data, trained using AIS labels, to detect vessels near cables; no accuracy or latency published — [Hartree, Feb 2026](https://www.hartree.stfc.ac.uk/case-studies/2026/02/23/transforming-subsea-cable-protection-through-real-time-vessel-detection/).
- **[RESEARCH] Marlinks-NS.** Open North Sea DAS dataset with AIS-derived labels: 74,771 labelled instances from ten days on a 2,554 m segment of a 28 km buried cable, for vessel detection and vessel-to-cable distance — [arXiv 2607.28306, Jul 2026](https://arxiv.org/abs/2607.28306). Possible real input for a cue model.
- **ESA DEEPSEA.** Real-time acoustic monitoring with existing fibre, detecting vessels without AIS — [ESA Business Applications](https://business.esa.int/projects/deepsea).
- A vendor guide says a platform may correlate DAS tracks with AIS, weather and route data, and cautions that an acoustic alert alone does not prove damage — [Hengtong Global](https://www.hengtongglobal.com/info/distributed-acoustic-sensing-submarine-cable-103693222.html).

**Range**
- Conventional DAS reaches about 100 km from one end, or 200 km from both — [CIGRE B1-10824, 2026](https://www.e-cigre.org/publications/detail/b1-10824-2026-early-detection-of-external-damage-incidents-in-long-distance-direct-current-submarine-cables.html).
- ASN puts its OptoDAS limit at 100 to 150 km or the first repeater — [Open Access Government, ASN profile, Mar 2023, VENDOR](https://www.openaccessgovernment.org/article/protecting-submarine-cables-enhanced-connectivity-subsea/155612/). Patent filings on multi-span DAS describe conventional range as typically limited to one fibre span — [US 12111204](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12111204); [US 12650334](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12650334) (via search summary; exact wording not pinned to one filing).
- Nokia multi-span DAS on the Oregon observatory cables recorded out to 300 and 350 km, deployed 5 Nov 2025 to 28 Jan 2026, versus about 65 and 95 km before — [Ocean Observatories Initiative](https://oceanobservatories.org/?p=37482).

**Speed and localisation**
- CIGRE field trial: a simulated 40 kg anchor impact was detected with a 68.4 m position error at 262.2 km, using remote optical amplifiers; trawl gear approach was seen about 15 seconds before contact; vessels of 14 and 19 GT were detected — [CIGRE B1-10824, 2026](https://www.e-cigre.org/publications/detail/b1-10824-2026-early-detection-of-external-damage-incidents-in-long-distance-direct-current-submarine-cables.html).
- The same paper says the Murray loop typically locates faults within about 1% of cable length, and that matching damage to AIS fails if AIS was off or the fault shows up long after impact — [CIGRE B1-10824, 2026](https://www.e-cigre.org/publications/detail/b1-10824-2026-early-detection-of-external-damage-incidents-in-long-distance-direct-current-submarine-cables.html).
- Anritsu claims optical fault location to within 10 m — [Anritsu application note, VENDOR](https://dl.cdn-anritsu.com/en-au/test-measurement/files/Application-Notes/Application-Note/MW90010A_EF1200.pdf).

**Real alarm-to-response baselines**
- **Eagle S, 25 Dec 2024.** Fingrid's outage coincided with the crossing at 12:26 EET; telecom operators' cable disruptions reached authorities in the evening; the patrol ship Turva was escorting by early evening; boarding was at 00:28 on 26 Dec — [Wikipedia](https://en.wikipedia.org/wiki/2024_Estlink_2_incident).
- **Fitburg, 31 Dec 2025.** Elisa detected damage shortly before 5 a.m. and the ship was seized around 11 a.m., roughly six hours later — [The Record](https://therecord.media/finland-arrests-crew-ship-suspected-cable-break); [gCaptain](https://gcaptain.com/baltic-shadow-games-finland-detains-cargo-ship-in-suspected-hybrid-attack/).
- **Newnew Polar Bear, 2023.** With no NATO-wide protocol and no systematic sharing, identifying the ship took hours — [Atlantic Council](https://www.atlanticcouncil.org/in-depth-research-reports/issue-brief/how-the-baltic-sea-nations-have-tackled-suspicious-cable-cuts/).

**Can it feed a fleet?** Elisa's planned service is aimed at authorities and owners — [Light Reading](https://www.lightreading.com/security/elisa-gives-its-subsea-cable-ears). No source reviewed shows DAS alarms feeding USV tasking.

### Inferences
- For a 25 × 10 km area, range is probably not the limit if the cables land nearby and carry fibre. Whether the two power cables have fibre is a scenario assumption the team must state.
- Word the alarm as a late cue: it says where damage happened and starts a backwards search of "who was within X km in the last Y minutes". It rarely prevents the cut. A juror will catch "early warning".
- A strong one-liner is the baseline: real incidents took hours from alarm to a state vessel on scene. Five boats already inside the box could beat this, but only state a number computed from the team's own sim speeds.
- Treat a fault alarm as a simulated interface. "Cable-owner alarm integration" is a claim only if labelled as a mock feed.

### Gaps
- No published alarm latency for Elisa or any commercial service.
- No Baltic-specific DAS range, or data on which Danish cables have sensing or fibre.
- No published false-alarm rate from an independent source.

## Who sells USV fleet autonomy or swarm coordination today, and what is shown publicly?

### Takeaway
Many sell it; few show it. Public multi-boat teaming demos are small (two to eight boats) and vendor-run. Operator ratios and comms-denied behaviour are mostly claims, and no vendor publishes how tasks are re-divided after a boat fails. The base scenario (search, spot, escort, resume) has already been shown by Shield AI on real water, and five USVs under one operator dates to 2014.

### Cited Findings

| Company | Publicly shown (date) | Boats | Operator model | Degraded comms | Grade |
|---|---|---|---|---|---|
| Shield AI + Thunder Tiger | Search box split into two sectors, roughly 2 km², radar, imagery and AIS; escorted a crewed target out with no human intervention (29 Jul 2026) | 2 | Autonomy stack; operator not described | Not stated; re-tasking after failure not addressed | DEMO/VENDOR ([Shield AI](https://shield.ai/shield-ai-and-thunder-tiger-complete-hiveminds-first-multi-asset-autonomous-maritime-teaming-demonstration-in-taiwan/), [Quwa](https://quwa.org/asia-pacific/taiwans-thunder-tiger-demonstrates-autonomous-usv-teaming-with-shield-ais-hivemind/)) |
| Shield AI + Kraken | Portsmouth: search with radar, cameras, AIS; escorted a vessel out; replanned and resumed search (announced 28 Sep 2026) | 2 K3 Scout | Human authority kept; "can reduce" one-operator-per-vessel | No link details; contested trials still planned | DEMO/VENDOR ([Baird Maritime](https://www.bairdmaritime.com/security/naval/unmanned-naval-systems/shield-ai-kraken-usv-mission)) |
| Saronic | Company-funded week 70+ nm offshore, five-day loiter, 92+ hour runs (Feb 2026 report) | 8 Corsair | Shore Joint Operations Center plus support craft; headcount not stated | Simulated comms-denied intercepts; internal nav and passive sensing | DEMO/VENDOR ([MarineLink](https://www.marinelink.com/news/saronic-completes-multiday-corsair-535338)) |
| HavocAI | Escort of Army ship; closest boat peeled off to counter a threat, others reformed (reported 14 Jul 2026) | 6 Rampage | CEO: "no humans in the loop" | Not addressed; tracks passed over Link 11/16 via SAIC router | DEMO/VENDOR ([Seapower](https://seapowermagazine.org/havocai-usvs-with-saic-routers-escort-army-ship-in-exercises/)) |
| HavocAI | GPS-denied air-sea demo, Troia, Portugal (Dec 2025) | Count not given | One operator, one screen | Claims missions held under disruption; navigation method unnamed | VENDOR ([Digital Ship](https://thedigitalship.com/news/electronics-navigation/havocai-proves-autonomy-without-gps-at-sea)) |
| Maritime Robotics | Formation simulating mothership protection, Trondheim Fjord (9 Apr 2026) | "Multiple" | Remote Operations Center, supervised autonomy | Not stated | DEMO ([Ocean Autonomy Cluster](https://oceanautonomy.no/en-us/oacnews/autonomy-at-sea-demonstrated-live-for-us-navy-in-trondheim)) |
| Saildrone | Danish three-month trial in Baltic and North Sea (from Jun 2025) | 4 Voyager | Remote fleet ops; not swarm | Not stated | DEMO ([CTV/AP](https://www.ctvnews.ca/sci-tech/article/denmark-tests-unmanned-robotic-sailboat-fleet-with-tensions-high-in-the-region/)) |
| SIS / ONR | Swarm I 2014: team under one operator, no safety riders or remote control. Swarm II 2016. USV Swarm 2019: eight heterogeneous | 5, 4, 8 | One operator (2014) | Not stated | DEMO ([Shephard, May 2019](https://shephardmedia.com/news/uv-online/sis-advances-usv-swarm-autonomy)) |

Other points:
- Shield AI's director of government relations for Asia said five USVs could cover "up to 8.3 times" their combined search area with Hivemind. No method given — [Quwa](https://quwa.org/asia-pacific/taiwans-thunder-tiger-demonstrates-autonomous-usv-teaming-with-shield-ais-hivemind/). **[VENDOR]**
- Saronic's Echelon is built for one operator to plan, simulate and run missions across multiple vessels (July 2025) — [Seapower](https://seapowermagazine.org/saronic-unveils-echelon-a-unified-platform-for-mission-planning-simulation-and-command-and-control-of-autonomous-surface-vessels/?print=pdf). A claim of about 100 vessels per operator is flagged as unvalidated at scale — [Sacra](https://sacra.com/chat/h/2a0723ac-a795-4bc6-b773-16e63d5a4bb5/). **[VENDOR, WEAK]**
- HavocAI's June 2025 fleet test described was a simulation with eight boats; all vessels share the same control software, and the article does not say whether coordination is central or distributed — [Resilience Media, 13 Jun 2025](https://resiliencemedia.co/startup-havocai-bets-big-on-autonomous-naval-drones-eyes-100-foot-platform-by-years-end).
- Anduril's April 2026 Kraken deal covers building K5 and K7 boats in the US with Lattice — [ASD News](https://asdnews.com/news/defense/2026/04/21/anduril-partners-with-kraken-technology-group-small-usvs). A Voltaic boat was integrated into Lattice at BlueTide 2026 — [Defense Daily, via search snippet](https://www.defensedaily.com/anduril-pitches-lattice-for-port-defense-demonstrates-sea-integration-at-bluetide/unmanned-systems/). No live multi-USV Lattice demo found.
- Helsing tested launching HX-2 from a speedboat near Plymouth (reported 11 May 2026); crewed or uncrewed not stated — [RBC-Ukraine, citing Militarnyi](https://newsukraine.rbc.ua/news/ukraine-tests-german-hx-2-strike-drones-launched-1778478182.html). No Helsing USV swarm found.
- Sea Machines sells STORMRUNNER, SM300 and autonomy kits (special operations contract reported Sept 2026) — [The Defense Post](https://thedefensepost.com/2026/09/14/sea-machines-us-maritime-autonomy/). Multi-boat demo not found.
- Seasats Lightfish was tested by US Sixth Fleet's CTF 66 at Cutlass Express 2026 — [Yahoo Tech/SlashGear](https://tech.yahoo.com/articles/us-navys-solar-powered-lightfish-083000053.html). Fleet coordination not found.
- Exail's DriX O-16 launches and recovers subsea robots, and Exail calls multi-robot missions the direction of travel — [ECO Magazine](https://ecomagazine.com/news/industry/exail-introduces-new-transoceanic-usv-with-multi-robot-deployment-capabilities/). No surface swarm found.
- **[FIELDED, combat] Ukraine.** Drone boats launched FPV drones against Russian air defences in January 2025 — [TWZ](https://twz.com/news-features/ukraine-claims-its-drone-boats-are-now-launching-kamikaze-fpv-drones-at-russian-shore-targets). Magura V5 is reported in US hands at Balikatan 2026, and Uforce and ReconCraft signed a US production MoU on 21 Jul 2026 — [Army Recognition](https://www.armyrecognition.com/news/navy-news/2026/ukraine-magura-usv-drone-us-production-uforce-reconcraft). Autonomy details are not public.
- The US DIU, DAWG (described as essentially a rebranded Replicator) and Navy launched a $100M Orchestrator prize in January 2026, for software that turns voice or text intent into coordinated action while keeping human oversight — [DIU](https://www.diu.mil/latest/diu-and-dawg-launch-autonomous-vehicle-orchestrator-prize-challenge); [Defense One](https://www.defenseone.com/technology/2026/01/pentagon-leans-drone-swarms-100m-challenge/410742/).

### Inferences
- A juror from this industry knows the Hivemind pattern. The team must not present "one boat keeps the contact while the other resumes" as new. It was publicly shown on real water with two boats in summer 2026, and the concept is older.
- The three things vendors publish least: what happens when a boat fails mid-task, how operators are counted, and any method behind headline numbers. That is the opening.
- Distributed versus central is not publicly settled by any vendor. Say "public sources don't show their architecture", not "they're centralised".

### Gaps
- Nothing usable found for Blue Water Autonomy, Ocean Aero, Thales, Kongsberg or Teledyne on multi-USV coordination; the searches returned no relevant results, which does not mean they have none.
- A claim that one HavocAI operator controlled 25 vessels across Europe, Rhode Island and San Diego appeared in a search summary, but the page checked did not contain it. Do not repeat it unverified.
- National Defense's 25 Jun 2026 HavocAI article could not be read in full.

## What have Task Force X Baltic, REPMUS, Dynamic Messenger, Task Force 59 and Replicator shown, and what gaps do they report?

### Takeaway
Large numbers, networked pictures, and almost no published coordination metrics. NATO sources are promotional and omit failure data. The honest gap reporting comes from US sources: software failures, collisions, integration problems, and station-keeping and COLREGS issues.

### Cited Findings
**NATO**
- **Task Force X Baltic.** Fully operational mid-June 2025, more than 70 uncrewed maritime and aerial systems, 24/7 at peak, about one month of continuous operation, tested in harsh weather, shallow water and electronic interference. Eight Baltic-region defence ministers signed a Letter of Intent about 14 months after the December 2024 disruption. The account omits autonomy levels, failure rates and performance metrics — [NATO Innovation Network, 11 Mar 2026](https://natoinnovation.network/2026/03/11/task-force-x/).
- Saildrone ran four Voyagers in the Gulf of Finland and western Baltic for at least 16 to 27 June 2025, tied to Dynamic Messenger; ACT was to provide 19 additional USVs — [Baird Maritime](https://www.bairdmaritime.com/security/naval/unmanned-naval-systems/nato-to-conduct-uncrewed-vessel-demonstrations-in-baltic-sea); [Naval Technology](https://www.naval-technology.com/news/nato-uncrewed-vessels-demonstration/). These read as surveillance deployments, not swarms.
- A May 2026 ACT article says activity is emerging in the Central Mediterranean, North Sea and Arctic, moving from experimentation to implementation — [NATO ACT, via search snippet](https://www.act.nato.int/article/tfx-baltic/).
- **REPMUS 2026.** 31 Aug to 25 Sep, Troia, over 3,700 participants, about 300 unmanned systems, 36 navies. TFX-Arctic's "connectivity backbone" was assessed, with a Norway trial due end of 2026 — [NATO, 8 Oct 2026](https://www.nato.int/en/news-and-events/articles/news/2026/10/08/repmus-2026-in-portugal-brings-together-nato-allies-to-test-uncrewed-maritime-systems).
- A simulated attack by more than 60 USVs and UAVs on a frigate, run by CTG Valhalla (Nordic participants and Ukraine), was described as experimental. Its outcome has not been published — [Brussels Times](https://www.brusselstimes.com/2354255/nato-maritime-exercise-tests-300-drones-in-push-for-uncrewed-supremacy); [Janes, via search snippet](https://www.janes.com/defence-intelligence-insights/defence-news/sea/repmus-2026-portuguese-navy-conducts-large-scale-counter-uxs-exercise).
- Syos linked USV contacts into the mission planner over common networks using a NATO STANAG for overlays, and concluded USVs are judged as nodes in a network — [Ocean News](https://oceannews.com/news/defense/syos-deploys-uncrewed-surface-vessels-at-repmus-nato-maritime-robotics-exercise/). Navies are described as seeking "jam-resistant, integrated uncrewed fleets" — [Shephard, 13 Oct 2026, paywalled](https://shephardmedia.com/news/naval-warfare/from-repmus-to-procurement-the-four-capabilities-nato-navies-want-from-usvs/).
- **Dynamic Messenger 2025** covered critical undersea infrastructure protection, persistent ISR and multi-domain C2 — [MARCOM](https://mc.nato.int/media-centre/news/2025/nato-advances-maritime-innovation-and-readiness-through-exercise-dynamic-messenger-2025). SitaWare Maritime gave one coalition picture across both sites, used for patrol areas and deconfliction zones — [Systematic, VENDOR](https://systematic.com/int/industries/defence/news-knowledge/cases/systematic-at-repmus25-and-dynamic-messenger/). No quantitative multi-USV results found.
- **BALTOPS 2026.** US GARCs played opposing force; spotting a USV was the hardest part for crews — [DVIDS, 15 Jun 2026](https://www.dvidshub.net/news/printable/568108).

**US**
- **Task Force 59, Digital Horizon (2022).** 17 partners, 15 systems, three weeks in Bahrain — [DVIDS/Navy](https://www.dvidshub.net/news/printable/435221). Vice Adm. Cooper listed mesh networking first among lessons, and one operator running multiple systems on one screen among them — [DefenseScoop, 12 Jan 2023](https://defensescoop.com/2023/01/12/5th-fleet-commander-reveals-takeaways-from-recent-exercise-with-ai-enabled-drones/).
- **Replicator, July 2025.** During a Navy test off California a boat stalled and another hit it; sources blamed software failures, human error, and breakdowns between onboard systems and external autonomy software. DIU paused a contract near $20M with L3Harris. Most details trace to one Reuters investigation with anonymous sources; the Navy, Saronic and BlackSea declined to comment — [gCaptain/Reuters](https://gcaptain.com/the-us-navy-is-building-a-drone-fleet-to-take-on-china-its-not-going-well/).
- WSJ reporting found glitches and problems integrating with command structures, and trouble buying software to command many drone types — [Responsible Statecraft](https://responsiblestatecraft.org/replicator/).
- **US Navy PMS 406, January 2024.** Across four USVs: 183 COLREGS interactions, over 80% as expected; 14 "inappropriate interactions"; rough seas caused false contacts and unneeded manoeuvres; USVs struggled to return to station such as a box or relative bearing and distance. Interventions of concern ran about once every 42 hours, and perception and autonomy issues about once every four days — [DefenseScoop, 19 Jan 2024](https://defensescoop.com/2024/01/19/navy-usv-inappropriate-interactions/).

### Inferences
- Reported problems sit in integration, comms between onboard and off-board software, and station-keeping, not in clever allocation. A demo that shows clean failure handling speaks to real pain.
- "Keep the vessel in view" is exactly the relative-station task the US Navy said USVs found hard. That is worth modelling.
- Saying "NATO's largest uncrewed fleet" in a pitch should be avoided; the phrase is self-reported. So is any comparison to REPMUS outcomes, which are unpublished.

### Gaps
- No public after-action report for TFX Baltic, REPMUS or Dynamic Messenger.
- A claim that Ukraine's red team beat NATO's blue team in five naval drone scenarios appears in a [secondary item](https://www.pulse.bot/defense/news/ukraine-says-its-red-team-forces-beat-natos-blue-team-forces-in-every-combat-scenario-during-recent-5e3d7c49-8df7-492e-b259-dadfd7927c11); its exercise and date were not confirmed.
- Whether the June 2026 procurement target tied to the Letter of Intent was met is unknown.

## Have similar projects appeared at EDTH or other defence hackathons?

### Takeaway
Yes on AIS anomaly detection, which is now common hackathon work. EDTH has run naval events, but no winners or maritime swarm projects could be found. No hackathon project found closes the loop from cable alert to coordinated boats, though Fincantieri's winner came near on multi-domain coordination.

### Cited Findings
- **EDTH overall.** 35 hackathons, over 400 teams, about 40 teams formed companies. Judging panels include military experts, defence companies and investors, with Ukrainian representation always present. Teams show working prototypes, not decks. Common themes include drones, autonomy, navigation, mesh networking and software-defined radios. No maritime project named — [tech.eu, 29 Jun 2026](https://tech.eu/2026/06/29/the-hackathon-that-become-europe-s-defence-startup-ecosystem/).
- **EDTH Naval Defense Tech Hackathon, Karlskrona, 7 to 10 May 2026.** At a naval base with the Marine Technology Center; Kraken was a demo participant ("Get wrecked by the best British USVs"). Challenges and winners not listed — [Luma](https://luma.com/edth-2026-karlskrona).
- A second Naval Defense Tech Hackathon was scheduled for 2 to 4 October 2026 in Galati, Romania, per a search summary; the [Luma page](https://luma.com/edth-2026-galati) returned 404 when fetched.
- **Philly 250 Maritime Defense Hackathon, 27 to 29 March 2026: HORMUZ WATCH.** Edge anomaly detection on live AIS (Isolation Forest and autoencoder on 18 features) trained on 18.8M NOAA records, alerts relayed over an ESP32 mesh, local LLM threat cards on a Jetson. It tasks no uncrewed assets. Prize not reported — [project page](https://maritimedefensecop.netlify.app).
- **SPASEA (Naval Group and DGA, Brest, 4 to 5 Dec 2025).** 27 hours; teams built decision support flagging suspicious vessels, such as AIS going off, from AIS, radar and satellite data, using LLMs. Winner: PosAIdon — [ENSTA](https://ensta.fr/en/accueil/news/artificial-intelligence-service-sailors-spasea-hackathon).
- **Fincantieri Maritime Security Hackathon (reported 15 Jun 2026).** Lares Technologies won with integrated management of autonomous underwater, surface and aerial vehicles, coordinating crewed and uncrewed platforms; five teams, 70+ participants — [MarineLink](https://www.marinelink.com/news/hackathon-spotlights-ai-autonomous-540311).
- **MarineHäkk 2026 (TalTech, 8 May 2026).** Team NOMAD won with a concept for a 24 m ice-capable USV with GNSS-free navigation; "dark vessel detection" was a challenge topic — [TalTech](https://taltech.ee/en/news/nomad-wins-marinehakk-2026-autonomous-naval-surface-drone-concept).

### Inferences
- If the team leads with AIS anomaly detection it looks like several earlier student projects, some with LLM threat cards too. Lead with fleet behaviour under failure.
- An ESP32 mesh has already appeared in a maritime hackathon, so cheap radios alone are not a differentiator.
- EDTH's working-prototype emphasis favours a live, breakable demo over a slide claim.

### Gaps
- Winners and projects for EDTH Karlskrona, Galati and past Copenhagen events were not found. Ask organisers or mentors directly; a similar project may exist unpublished.
- Whether challenge 07 was run at an earlier EDTH event is unknown.

## For each of the six ideas: fielded, researched, or open? What is the closest thing and the sharpest honest claim?

### Takeaway
None of the six is a new idea alone. Ideas 3 and 4, joined together, are the least shown publicly for USVs. Idea 1's last mile is the most mission-relevant gap. Idea 2 is known and should be sold on measurement. Idea 5 adds credibility, not novelty. Idea 6 is fielded and off-brief.

### Cited Findings

| # | Idea | Status | Closest existing thing | Left open (public sources) |
|---|---|---|---|---|
| 1 | Patrol the ships | Detection **fielded**; alert-to-boat tasking **not shown publicly** | Windward, Nordic Warden, Vesper/NKT; Hivemind for boat side | A cable alert becoming a boat task with a measured patrol cost |
| 2 | Named deputy | **Researched** since 1998; middleware exists | ALLIANCE; DDS Ownership | USV-specific gap measurements |
| 3 | Tamper-evident log | Technique **fielded elsewhere**; USV swarm version **not found** | Windward timelines; hash-chained audit logs | Peer-held chain across boats |
| 4 | Spoofed boat | **Researched** for UAVs in simulation; USV version **not found** | UWB and RSSI cross-checks | USV peer quarantine, with sensor data kept |
| 5 | Real radios | **Fielded** tech; **done at a hackathon** | HORMUZ WATCH ESP32 mesh | Nothing new; demo value only |
| 6 | Drone from boat | Launch **fielded in combat** | Ukrainian FPV carriers | Recovery onto a 2–3 m boat not found |

**Idea 1 (patrol the ships).** See the first key question for the fielded detection layer and the second for alarms. Real cases show AIS-on behaviour matters: tankers over pipelines did not go dark, and a trawler over cables had no AIS gaps — [Windward](https://windward.ai/blog/vessels-loiter-over-subsea-cables-and-pipelines-across-five-theaters/). Yi Peng 3 slowed and stopped over three cables off Læsø on 7 November 2024, per TV2 and partners' track analysis — [Maritime Executive](https://maritime-executive.com/article/chinese-bulker-accused-of-cutting-baltic-cables-may-have-tried-once-before). A 7.5-hour AIS gap after Gotland comes only from a [Wikipedia mirror](https://wiki.krisyotam.com/content/wikipedia_en_all_nopic_2026-03/2024_Baltic_Sea_submarine_cable_disruptions) **[WEAK]**. The Danish navy shadowed Yi Peng 3 into the Kattegat in 2024 — [Maritime Executive](https://maritime-executive.com/article/denmark-guards-chinese-bulker-that-may-have-caused-subsea-cable-damage), a local precedent for crewed shadowing.

**Idea 2 (named deputy).**
- ALLIANCE (Parker, 1998) is fully distributed; its "impatience" motivation lets a robot take over a task when others fail — [OSTI](https://www.osti.gov/biblio/34318).
- Stancliff, Dolan and Trebi-Ollennu argued reliability should be built into the initial plan instead of replanning after failure — [CMU RI](https://ri.cmu.edu/?p=10341).
- DDS Ownership gives each instance one owner, the live writer with highest strength; when the owner stops asserting liveliness, ownership passes to the next strongest, with ties broken by GUID. The docs say this is often used for standby redundancy, and that readers may switch at different times — [RTI Connext docs](https://community.rti.com/static/documentation/connext-dds/current/doc/manuals/connext_dds_professional/users_manual/users_manual/OWNERSHIP_QosPolicy.htm).
- ROS 2 QoS already has a liveliness lease duration — [ROS docs](https://docs.ros.org/en/jazzy/p/rosgraph_msgs/msg/QoSProfile.html).
- CBBA task allocation under weak links is active work for AUVs — [JMSE 2026](https://www.mdpi.com/2077-1312/14/3/237).

**Idea 3 (evidence log).**
- Windward logs time-stamped timelines for replay and investigation — [Windward](https://windward.ai/solutions/maritime-infrastructure/), and describes imagery as timestamped evidence — [Windward TSO page](https://windward.ai/industries/transmission-system-operators/).
- A project page describes hash chains for maritime audit logs and says a law opinion and insurer pilot are still needed — [edgesentry-rs](https://edgesentry.github.io/edgesentry-rs/legal/). A paper applies forensic hashing to voyage data recorders — [IJECE](https://ijece.iaescore.com/index.php/IJECE/article/view/20666).
- Logs a party generated itself can be attacked on the grounds the keeper could have altered them — [OriginStamp, citing Sedona Conference, VENDOR](https://originstamp.com/en/blog/reader/digital-evidence-admissibility-integrity-requirements).
- Under eIDAS Article 41, a qualified electronic time stamp carries a presumption of date accuracy and data integrity; a simple one only cannot be refused solely for being electronic — [eIDAS text](https://www.legislation.gov.uk/eur/2014/910/article/41/data.pdf).
- Real cases failed on jurisdiction and intent, not on tampered data. Helsinki District Court dismissed Eagle S for lack of jurisdiction in October 2025; damage was in the EEZ and jurisdiction lay with the flag state or crew's countries — [gCaptain](https://gcaptain.com/finnish-court-dismisses-case-against-eagle-s-crew-in-baltic-sea-cable-breach-trial); [Moscow Times](https://www.themoscowtimes.com/2025/10/03/finland-dismisses-case-over-baltic-cable-cuts-a90705). Vezhen was shelved for lack of proof of intentional anchor release — [Atlantic Council](https://www.atlanticcouncil.org/in-depth-research-reports/issue-brief/how-the-baltic-sea-nations-have-tackled-suspicious-cable-cuts/). Sweden found no evidence Yi Peng 3 acted intentionally — [gCaptain](https://gcaptain.com/swedish-probe-finds-no-conclusive-evidence-of-deliberate-cable-damage-by-chinese-ship/).
- In the Fitburg case the ship was caught in Finland's EEZ while the damage lay in Estonia's — [gCaptain](https://gcaptain.com/baltic-shadow-games-finland-detains-cargo-ship-in-suspected-hybrid-attack/).

**Idea 4 (spoofed boat).**
- Interference is real and rising locally: a Bornholm station logged 11 incidents in 2024, 16 in 2025 and 30 so far in 2026 — [EUalive citing DR, 10 Aug 2026](https://eualive.net/denmark-records-record-gps-disruptions-near-bornholm-as-baltic-interference-intensifies/).
- GPSPatron and Gdynia Maritime University found combined GPS spoofing and jamming, with clusters of ships at the same false position, from "a distributed, multi-node interference system" at fixed sites — [Maritime Executive, 22 Dec 2025](https://maritime-executive.com/article/study-baltic-gps-disruption-comes-from-a-tactically-controlled-network).
- UAV swarm detection exists: comparing GPS distance to UWB ranging between members — [Mykytyn et al.](https://export.arxiv.org/abs/2301.12766); a GNN comparing GPS and comms topology, over 90% accuracy with 10 UAVs in simulation — [Dang et al.](https://aaltodoc.aalto.fi/items/0b2cd50b-ebbb-49f6-b26f-f77c06d7cef1); BDGD uses RSSI distance checks and reputation scores to isolate spoofed UAVs — [RESS 2026](https://pure.ecnu.edu.cn/en/publications/enhancing-the-resilience-of-uav-networks-against-gps-spoofing-att/); IMU plus neighbour checks in simulation — [MILCOM 2023](https://www.aminer.org/pub/658d4fab939a5f40824511ca/towards-effective-swarm-based-gps-spoofing-detection-in-disadvantaged-platforms).
- A survey says systemic swarm weaknesses remain under-examined, with a gap between detection and real-time countermeasures — [Abima et al.](https://researchportal.beds.ac.uk/p/en/research-outputs/a-survey-ongnss-spoofing-attacks-onuav-swarms-challenges-current-).
- R-Mode Baltic is a terrestrial backup using maritime beacons; one station can validate GNSS even without giving a fix — [DLR](https://www.dlr.de/en/kn/research-transfer/projects/maritime-security/ormobass/prototype-mf-r-mode-receiver). IMO draft receiver standards go to MSC 112 in December 2026 — [DLR](https://www.dlr.de/en/kn/research-transfer/projects/maritime-security/r-mode-baltic-and-r-mode-baltic-2).
- HavocAI and Saronic describe GPS-denied or internal navigation, which addresses losing GPS, not a peer quietly lying — [Digital Ship](https://thedigitalship.com/news/electronics-navigation/havocai-proves-autonomy-without-gps-at-sea); [MarineLink](https://www.marinelink.com/news/saronic-completes-multiday-corsair-535338).

**Idea 5 (radio boards).**
- TF59 listed mesh operations first among lessons — [DefenseScoop](https://defensescoop.com/2023/01/12/5th-fleet-commander-reveals-takeaways-from-recent-exercise-with-ai-enabled-drones/). Silvus markets swarm and relay links for USVs — [Silvus, VENDOR](https://silvustechnologies.com/applications/unmanned-systems).
- HORMUZ WATCH used an ESP32 mesh — [project page](https://maritimedefensecop.netlify.app). A hardware-in-the-loop UAV setup used Microhard radios — [arXiv 2506.20626](https://arxiv.org/pdf/2506.20626). Mesh and SDR are common at EDTH — [tech.eu](https://tech.eu/2026/06/29/the-hackathon-that-become-europe-s-defence-startup-ecosystem/).

**Idea 6 (drone from boat).**
- Ukraine launched FPVs from USVs against gas platforms (Dec 2024) and air defences (Jan 2025) — [TWZ](https://twz.com/news-features/ukraine-claims-its-drone-boats-are-now-launching-kamikaze-fpv-drones-at-russian-shore-targets).
- Helsing tested HX-2 launch from a speedboat — [RBC-Ukraine](https://newsukraine.rbc.ua/news/ukraine-tests-german-hx-2-strike-drones-launched-1778478182.html). HavocAI claims air-sea integration — [Digital Ship](https://thedigitalship.com/news/electronics-navigation/havocai-proves-autonomy-without-gps-at-sea).
- Danish firm Upteko builds ship-based drones; no landing on a moving vessel confirmed — [CORDIS](https://cordis.europa.eu/project/id/876257).
- No demonstration of a UAV landing on a small USV was found.

### Inferences

**Idea 1.**
- Say: "We don't compete on detection. Services like Nordic Warden and Windward already flag risky ships. We take that kind of alert and turn it into one boat's job, and show what it costs the patrol."
- Avoid: "first to fuse AIS for cables", "early warning from cable alarms", "we detect dark ships". Boats have a camera and AIS only, so a dark contact can be seen only within camera range.
- Label the crossing predictor as simple dead reckoning on simulated traffic.

**Idea 2.**
- Say: "An old idea applied to boats. The backup is agreed in advance, so takeover needs no new message. We measure the gap against re-auctioning."
- Avoid: "no radio traffic", because the lease is renewed by heartbeats. Avoid "novel". A juror who knows ROS 2 or DDS will say "that's ownership strength".
- Be ready for split-brain: the owner may be alive with a dead link, so two boats briefly do the same task. Answer: "we accept duplicates, never gaps", plus a fixed tie-break like DDS's. Also cover the deputy dying too (a chain of deputies).

**Idea 3.**
- Say: "Each boat hash-chains its log and peers hold its latest hash, so one lost or altered boat can't silently rewrite the record. It shows tampering. It doesn't prove the data is true, and we make no claim on admissibility."
- Avoid: "court-ready", "legally admissible", "blockchain", "tamper-proof".
- Key move: past cases turned on jurisdiction and intent. A report that records ship track against zone lines, speed pattern and time near the cable answers what those cases lacked better than cryptography alone.

**Idea 4.**
- Say: "A boat can be alive, connected and wrong. If its GPS disagrees with what peers measure, the swarm stops trusting its position, keeps its video, and moves its job."
- Avoid: "we detect spoofing" as a general claim. Baltic interference comes from multi-node transmitters, so nearby boats may all shift together, and peer checks can't see that. State this limit first; a juror will raise it. For area-wide spoofing, note a fallback (shore link, R-Mode as future input, visual fixes).
- The check needs a measurement that doesn't depend on GPS. The challenge kit gives camera bearings and radio. RSSI over water is likely noisy, so simulate its error honestly.
- Join ideas 3 and 4: a perfect log can faithfully record a false position, so entries should carry a position-trust flag. This pairing is the most original combination found.

**Idea 5.**
- Say: "Nothing new here. It proves the failure isn't scripted: unplug a board and watch."
- Avoid: "jam-resistant", "tactical radio" or range claims. The boards show link-loss behaviour, not RF performance.
- Keep it if it costs little; do not let it eat core build time.

**Idea 6.**
- Recommend dropping from the core. It is fielded in combat, the challenge kit has no drone, and a 2D simulator can't show launch or recovery. The team's drone-vision strength makes it tempting, but it would not count as new.
- If kept, use only as a one-shot check of a contact before pulling a boat off patrol, and say so as a concept.

**Originality ranking (judgement):** ideas 3 and 4 joined, then 1 (last mile), then 2, then 5, then 6.

**Overall claim to use:** "Public demos show two boats finding a ship, or eight running for a week. We show what public sources don't: five boats losing two members and one lying about where it is, with the cable watch measured in numbers and the operator approving instead of steering." Use only if the numbers are real, and say "in public sources we found".

### Gaps
- The DDS comparison rests on RTI's documentation, not a USV deployment.
- No admissibility ruling found on hash-chained maritime data, and no C2PA or eIDAS-camera precedent checked.
- A claim that shadow-fleet tankers act as spoofing transmitters surfaced in search but could not be tied to a primary source, and the GPSPatron study points to fixed sites. Don't rely on it for a "the target spoofed our boat" story without labelling it hypothetical.
- The Atlantic Council brief says the Danish Straits count as international waters. That is a simplification; check the actual legal regime with a Danish lawyer or the Naval mentors before quoting it. Much of the scenario area may be Danish territorial sea, which would change the jurisdiction argument from Eagle S.

## Is there a stronger differentiator, buildable in about 40 hours in a 2D simulator?

### Takeaway
Yes. The best one is not a feature but a published, repeatable failure scorecard, because nobody public gives these numbers. Three cheap additions sharpen it: law-aware incident reports, a COLREGS-aware shadowing rule, and a reserve rule so false alarms and decoys can't empty the cable.

### Cited Findings
- Public accounts skip the numbers: Shield AI's release does not address re-tasking after failure — [Shield AI](https://shield.ai/shield-ai-and-thunder-tiger-complete-hiveminds-first-multi-asset-autonomous-maritime-teaming-demonstration-in-taiwan/). TFX accounts omit failure rates and metrics — [NATO Innovation Network](https://natoinnovation.network/2026/03/11/task-force-x/). The REPMUS 2026 outcome is unpublished — [Brussels Times](https://www.brusselstimes.com/2354255/nato-maritime-exercise-tests-300-drones-in-push-for-uncrewed-supremacy). The headline "8.3 times" comes with no method — [Quwa](https://quwa.org/asia-pacific/taiwans-thunder-tiger-demonstrates-autonomous-usv-teaming-with-shield-ais-hivemind/).
- Jurisdiction decided Eagle S — [gCaptain](https://gcaptain.com/finnish-court-dismisses-case-against-eagle-s-crew-in-baltic-sea-cable-breach-trial). The Atlantic Council brief says the response is up to the coastal state, and that cable owners hold primary responsibility for security — [Atlantic Council](https://www.atlanticcouncil.org/in-depth-research-reports/issue-brief/how-the-baltic-sea-nations-have-tackled-suspicious-cable-cuts/).
- The US Navy found that compliant but unexpected manoeuvres still matter, that false contacts trigger needless COLREGS moves, and that holding a relative bearing and distance was hard — [DefenseScoop](https://defensescoop.com/2024/01/19/navy-usv-inappropriate-interactions/).
- Skylight warns its flags catch harmless movement — [Skylight docs](https://skylight.helpjuice.com/en_US/dark-rendezvous). Windward rated a trawler over cables only "moderately suspicious" — [Windward](https://windward.ai/blog/vessels-loiter-over-subsea-cables-and-pipelines-across-five-theaters/). Even a claimed 1 to 3% false-positive rate is non-trivial given 34,081 Q2 activities near cables worldwide — [TeleGeography](https://resources.telegeography.com/protecting-internet-infrastructure-submarine-cable-sensing); [Windward](https://windward.ai/knowledge-base/q2-2026-undersea-cables-risk-report/).
- DIU's Orchestrator aims to preserve human oversight while translating intent to action — [DIU](https://www.diu.mil/latest/diu-and-dawg-launch-autonomous-vehicle-orchestrator-prize-challenge). NATO evaluators treat USVs as network nodes — [Ocean News](https://oceannews.com/news/defense/syos-deploys-uncrewed-surface-vessels-at-repmus-nato-maritime-robotics-exercise/).

### Inferences
Ranked by value for effort (judgement, not sourced):

1. **Failure scorecard.** Run many randomised failure seeds and report worst revisit time per cable kilometre, handover gap, seconds of contact lost, approvals per hour, and comparison against a static patrol and a re-auction baseline. A curve, with the method shown, beats any vendor headline. It also protects every other claim, since each idea gets a number. This is mostly scripting over an existing simulator.
2. **Reports that answer the Eagle S questions.** Draw territorial-sea and EEZ lines in the sim. The incident report says which zone the ship was in at each event, who the likely responsible state is, and what was seen versus inferred. Small effort, and few hackathon teams will think of it. Have it checked by a mentor, since the legal labels must be right.
3. **Reserve rule against decoys and false alarms.** A low-confidence cue may not take the last boat off a cable segment. Show a two-ship test: one ship loiters as a decoy and draws a boat, while a second approaches another stretch. Report how much coverage survives. No public source reviewed tests this. It is a red-team scenario the team invents, so call it that.
4. **COLREGS-aware shadowing.** The shadowing boat holds a set distance and bearing, gives way correctly near the lane, and yields when a crossing ship has priority. It matches a real reported difficulty, and the "busy shipping lane" makes it expected.
5. **Authority leases for the operator.** Approvals expire. If shore is lost, boats act only inside pre-agreed limits, such as keeping a contact in view at standoff. This answers "what happens when the operator can't be reached?", and it reuses the idea 2 machinery. Report approvals per hour as the measure of operator load.
6. **Open output.** Export tracks in a NATO-friendly or common format, so the swarm reads as a node. Only claim what is implemented; "STANAG-compliant" would be false unless it truly is.

Suggested order for 40 hours: base design; failure scorecard; spoofed boat plus evidence log (joined); named deputy; reserve rule; COLREGS shadowing; law-aware report; authority leases. The patrol-the-ships alert feed can stay a mock interface. Treat real radio boards as optional and drop the drone.

### Gaps
- Vessel visual re-identification between boats (handing over a contact by appearance) would suit the team's vision skills, but its prior art was not researched and a 2D sim can't show it.
- Whether decoy behaviour has been observed in real cable incidents was not found.
- Build-effort views above are judgement, not measured.
