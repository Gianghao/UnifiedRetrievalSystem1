# Four-week research team work plan

These five member briefs turn the team's research proposal, **Unified Retrieval Across Heterogeneous Information Sources**, into individual research questions, practical tasks, and presentation deliverables. Each member owns a workstream and contributes to one integrated result.

## Team and workstream mapping

| Member | Workstream | Individual brief |
|---|---|---|
| Hào — team leader | Research methodology, coordination, and integration | [Hao](hao-methodology-lead.md) |
| Tài | Speech recognition, media processing, and ASR-error analysis | [Thiện](thien-asr-media-processing.md) |
| Quân | Dense retrieval and embeddings | [Quân](quan-dense-retrieval.md) |
| Thiện | BM25, retrieval strategies, and reranking | [Tai](tai-retrieval-reranking.md) |
| Xuân Ngân | Benchmark, evidence annotation, and evaluation | [Xuân Ngân](xuan-ngan-benchmark-evaluation.md) |

This mapping follows the five roles in the proposal and the strengths provided by the team. Thiện's AI-detection strength is applied to examining how recognition errors affect downstream search; Quân's AI and broad research background supports embedding work; Xuân Ngân's research and product-development strengths support a usable, defensible benchmark. Confirm the assignment together in the first team meeting if anyone prefers to swap ownership.

## Shared research objective

**How effectively can a unified retrieval system retrieve relevant information across heterogeneous sources, and how do retrieval strategy and source type affect accuracy, latency, and answer faithfulness?**

The prototype searches text messages, PDFs, audio transcripts, and video transcripts through one text-based retrieval pipeline. Retrieval evaluation is the primary contribution. Answer generation and summarization are secondary.

## Shared experimental rules

- Treat H1–H4 in the proposal as testable hypotheses, not results to confirm.
- Keep the corpus, queries, chunking, evidence labels, and evaluation protocol fixed across retrieval configurations.
- Compare BM25, BGE-M3 dense retrieval, and dense retrieval followed by BGE-reranker-v2-m3; consider hybrid retrieval only as an explicitly scoped optional condition.
- Do not disclose the correct source type to the system during the main unified-index experiment. Group results by source type only during analysis.
- Report retrieval quality separately from answer-generation quality. Use one fixed generator, prompt, and decoding configuration if running the secondary answer-faithfulness experiment.
- Use synthetic or consented materials. Do not place private chat exports, personal recordings, credentials, or other sensitive material in shared test data.
- Record model/version, processor/version, settings, data split, runtime hardware, and latency for each run. Do not report unverified improvements.

## Four-week rhythm

| Week | Team checkpoint | Evidence of progress |
|---|---|---|
| 1 | Agree on the research scope, definitions, architecture, and baseline choices | Each member has a short evidence-backed model/method note; research questions and interfaces are agreed |
| 2 | Build and demonstrate minimum components independently | Each workstream has a reproducible small example with configuration and limitations |
| 3 | Integrate on one controlled corpus and annotate the initial benchmark | One query path spans all four source types; initial evidence retrieval can be scored |
| 4 | Freeze the protocol, run preliminary comparisons, and prepare the presentation | Reproducible tables, clear caveats, integrated demo, and defensible proposed contribution |

## Shared acceptance criteria

By the presentation, the team can explain the research question, justify the selected methods, run a small reproducible cross-source retrieval demonstration, show preliminary evidence-based metrics, explain limitations, and distinguish observed findings from hypotheses. The target of 20–30 manually annotated questions is an initial proof-of-concept set, not a final benchmark.

See each member brief for specific questions, tasks, handoffs, and presentation responsibilities.
