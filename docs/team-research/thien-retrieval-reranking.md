# Thiện — BM25, Retrieval Strategies, and Reranking Researcher

**Team role:** Member 4 in the research proposal  
**Primary ownership:** Build the lexical baseline and reranking comparison, and quantify quality–latency trade-offs.

## Mission

Implement a proper BM25 baseline and a dense-plus-cross-encoder reranking condition that can be compared against Quân's dense search. Keep candidate retrieval and reranking separately measurable so the team can tell whether a failure comes from candidate generation or reranking.

## Questions to investigate

1. When does BM25 work especially well for exact identifiers, names, codes, and dates?
2. Does BGE-reranker-v2-m3 improve nDCG@10 and evidence completeness over dense retrieval alone?
3. How much latency does reranking add, especially when 50 candidates are scored to return the top 10?
4. Is evidence missing because the initial candidate set did not contain it, or because the reranker ranked it too low?
5. Does a hybrid BM25+dense method improve cross-source or mixed lexical/semantic questions enough to justify its added complexity?
6. Are quality and latency trade-offs different across source types and question types?

## Research tasks

- Study BM25 term-frequency/inverse-document-frequency behavior, tuning options, and known limitations.
- Study cross-encoder reranking and BGE-reranker-v2-m3's intended use, multilingual characteristics, input limits, and runtime cost.
- Define a common top-k result contract with Quân and Hao; preserve chunk IDs, source locations, and candidate scores.
- Implement BM25 as a distinct lexical baseline. Do not substitute BGE-M3's learned sparse output for BM25.
- Implement dense top-50 then rerank-to-top-10 as the initial reranking comparison, if the hardware and runtime permit; record any changed cutoffs.
- Record candidate recall before reranking, reranking time separately, final ranking metrics, and total p50/p95 latency.
- Treat hybrid retrieval (for example, reciprocal-rank fusion) as optional. Scope it only after the main three conditions work.

## Technical work

- Build an indexable BM25 corpus using the same canonical text chunks as dense retrieval.
- Expose interchangeable baseline, dense, and dense-plus-reranker methods behind a consistent interface or script entry point.
- Log configuration, top-k counts, timing, source IDs/locations, and failure status per query.
- Supply all ranked outputs and run metadata to Xuân Ngân's evaluator.
- Check that no method receives the gold answer, required evidence labels, or correct source type as input.

## Four-week checkpoints

### Week 1 — Algorithm and protocol

- Prepare short BM25 and cross-encoder notes with model details and constraints.
- Agree on shared corpus, chunking, candidate/result schema, and latency measurement conditions.

### Week 2 — Minimum comparison

- Demonstrate BM25 on a fixed set of sample questions.
- Demonstrate dense candidates reranked by the selected cross-encoder, or identify hardware/runtime blockers early.
- Record candidate count, returned count, timing, and configuration.

### Week 3 — Pilot runs

- Run all primary retrieval configurations against the shared pilot queries.
- Analyze missing-candidate cases separately from reranking-order failures.
- If time allows, run a clearly marked hybrid condition without replacing the primary comparisons.

### Week 4 — Results and explanation

- Provide preliminary ranking metrics and p50/p95 latency per configuration and source/query category.
- Prepare examples illustrating lexical, semantic, and reranking behavior.
- Explain the quality–latency trade-off and limitations in the presentation.

## Deliverables and acceptance checklist

- [ ] Reproducible BM25 index/search baseline.
- [ ] Dense-plus-reranker condition with documented candidate and final top-k values.
- [ ] Separate candidate recall, reranker latency, and end-to-end latency logs.
- [ ] Results in a format that the common evaluator can consume.
- [ ] Preliminary comparison with nDCG@10, Recall@10, MRR@10, Complete Evidence@10, and latency where supported by labels.
- [ ] Failure analysis with representative examples and no unsupported performance claims.

## Handoffs and presentation segment

Coordinate candidate inputs/results with Quân; provide ranked run outputs and timing metadata to Xuân Ngân; agree on the controlled matrix with Hao; consume Tài's transcript variants for the ASR experiment. Your presentation section defines BM25 and reranking, shows how they compare, and makes the added latency visible.

## Risks to watch

- Tuning BM25 or reranker settings on the final evaluation questions and then reporting those same questions as an unbiased test.
- Hiding poor candidate recall behind reranker results.
- Mixing candidate-generation latency with reranking latency or reporting only an average.
- Changing top-k or chunking between runs without logging it.
- Claiming hybrid improvement from a tiny pilot without uncertainty or replication.
