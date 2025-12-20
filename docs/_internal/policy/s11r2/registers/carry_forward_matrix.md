# Carry-forward matrix (verbatim vs adapted)

This matrix records whether extracted draft-2 items were carried forward verbatim or adapted (and why). It is the anti-drift companion to `draft2_preservation_map.md`.

| CF ID | Preservation item (P-####) | Source anchor | Destination doc + anchor | Posture (`verbatim`/`adapt`) | Rationale (if adapt) | Reviewed by | Date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CF-0001 | P-0001 | D2-0003 §Decision outcome → Pipeline | `docs/_internal/adr/0003-execution-contract-foundation.md`#decision-outcome | adapt | Align with plan v19 Resolution Domains and artifact specs | | 2025-12-20 |
| CF-0002 | P-0002 | D2-0003 §Immutability | `docs/_internal/adr/0003-execution-contract-foundation.md`#decision-outcome | verbatim | | | 2025-12-20 |
| CF-0003 | P-0003 | D2-0003 §Decision visibility | `docs/_internal/adr/0003-execution-contract-foundation.md`#decision-outcome | adapt | Align disclosure with run summary + run artifacts contracts | | 2025-12-20 |
| CF-0004 | P-0004 | D2-0003 §Policy domains | `docs/_internal/adr/0003-execution-contract-foundation.md`#decision-outcome | adapt | Recast as Resolution Domains to match plan | | 2025-12-20 |
| CF-0005 | P-0005 | D2-0003 §Runner vs Executor roles | `docs/_internal/adr/0003-execution-contract-foundation.md`#decision-outcome | verbatim | | | 2025-12-20 |
| CF-0006 | P-0006 | D2-0003 §Structured findings | `docs/reference/findings.md`#finding-schema | adapt | Formal schema belongs in reference spec | | 2025-12-20 |
| CF-0007 | P-0007 | D2-0001 §Canonical matching basis | `docs/_internal/adr/0006-paths-foundation.md`#decision-outcome | adapt | POSIX-only posture per policy vCurrent | | 2025-12-20 |
| CF-0008 | P-0008 | D2-0001 §Output path resolution rules | `docs/reference/path_resolution.md`#resolution-contract | adapt | Normalize under paths foundation | | 2025-12-20 |
