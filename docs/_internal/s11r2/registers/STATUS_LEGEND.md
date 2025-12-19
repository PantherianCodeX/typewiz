# STATUS_LEGEND.md — s11r2 Rewrite Governance System

| Code | Label | Meaning | Allowed when | Typical next step |
| ---: | --- | --- | --- | --- |
| **NS** | Not Started | Question logged, but no real investigation begun. | You’ve identified a gap/ambiguity and captured it, but haven’t reviewed sources. | Move to **IP** once sources are being reviewed. |
| **IP** | In Progress | Actively investigating; sources are being consulted and options refined. | You are reading draft-2, plan-v18, specs, code/help snapshots, etc. | Move to **RV** when you have a candidate resolution ready for review. |
| **RV** | In Review | Proposed resolution exists and is awaiting maintainer decision / review gate. | You’ve listed options, preferred option, and the intended owner doc(s). | Move to **DN** if accepted, or back to **IP** if rejected/needs more work. |
| **DN** | Done | Decision made and recorded (with a stable reference), and work is unblocked. | The decision is captured in an ADR/spec/policy change record, and mapping/owners updated. | Remains **DN**; optionally add a link to the merged evidence. |
| **BL** | Blocked | Work cannot proceed (or must not proceed) until this is resolved. | Continuing would require invention, or affects scope/behavior materially. | Move to **IP** once someone is actively working it, or **RV** if solution queued. |
