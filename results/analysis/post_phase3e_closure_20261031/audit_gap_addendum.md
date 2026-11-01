# Audit Gap Closure Addendum

This addendum closes only documentation gaps identified by the research artifact audit. It does not alter prior reports, raw logs, summaries, manifests, or historical data.

- Phase 3A older runs retain environment and manifest evidence, but missing immutable source revisions and some exact command capture cannot be reconstructed. This is a provenance/reproducibility limitation, not a correctness defect.
- Phase 3B/3B.1/3C and Phase 3D can be reproduced with the existing environment and saved scripts/artifacts, but no retroactive dependency lock or source commit hash is claimed.
- Phase 3E `_02` is canonical. Its input hashes and exact output directory are recorded in the closure manifest. The runner was working-tree based; no historical commit hash is invented.
- RSS values are explicitly interpreted as the saved macOS `ru_maxrss / 1024` readings. They remain comparable within this run on this host only.
- U=111 remains unclassified. The closure does not infer optimality from U=112 SAT.
