# Synthetic retrieval simulation

Twelve seeded input orders, 20 synthetic sources each, top eight retrieval hits. Gold means a valid explicit partition with residual 2; it does not mean historical truth. Channels and local arithmetic/type checks are real implementation calls. The six ablations below test component combinations, not six fully implemented research frameworks.

| Combination | Mean recall | Mean precision | Mean wrong-type/invalid candidates |
|---|---:|---:|---:|
| BM25 only | 1.000 | 0.250 | 6.00 |
| Lexical + fuzzy | 1.000 | 0.250 | 6.00 |
| Typed only | 1.000 | 0.667 | 1.00 |
| Hybrid RRF | 1.000 | 0.250 | 6.00 |
| Typed + constraints | 1.000 | 1.000 | 0.00 |
| Hybrid + constraints | 1.000 | 1.000 | 0.00 |

Interpretation: typed retrieval handles changed cardinalities without textual identity. Guarded outputs are a comparison shortlist; all rejected or undisplayed source records remain in custody. The fixture favors the explicit partition schema and does not evaluate metaphor, morphology, OCR, unknown languages, broader motifs, source truth, large-corpus scaling, or external acquisition. Reordering a small corpus is a reproducibility stressor, not independent evidence about real research performance.

The six submitted recommendation families are evaluated separately in PIPELINE_DESIGN.md. MCTS/BALD, full e-graphs, d-DNNF, sheaves and neural components have not been benchmarked by this script.
