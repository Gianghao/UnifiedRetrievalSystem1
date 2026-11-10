# Quân — Dense Retrieval and Embedding Researcher

**Team role:** Member 3 in the research proposal  
**Primary ownership:** Investigate semantic vector retrieval and make it reproducible across all four source categories. Your AI, robotics, and broad research background supports examining model behavior and engineering trade-offs.

## Mission

Build the dense-retrieval condition for the unified prototype using BGE-M3 dense embeddings, then analyze when semantic search helps or fails compared with lexical search. Keep the model, vector configuration, chunking, and metadata stable enough for fair comparison.

## Questions to investigate

1. Does BGE-M3 retrieve relevant evidence when a question paraphrases the wording in the source?
2. Where does BM25 remain competitive or better, especially for exact names, codes, dates, and technical terms?
3. Does dense retrieval behave consistently across messages, PDFs, audio transcripts, video transcripts, and cross-source questions?
4. What effects do chunk size, overlap, embedding normalization, similarity function, and language have on results?
5. What are the memory, indexing, and query-latency costs for the pilot corpus?
6. Can every vector result retain its original message/file ID and page or time location?

## Research tasks

- Study embedding and vector-similarity concepts and BGE-M3's documented model characteristics, training objectives, multilingual behavior, and intended use.
- Compare BGE-M3 with one alternative embedding model using a small, fixed set of representative queries if time permits. Do not change the primary model without documenting why.
- Keep the experiment to BGE-M3's dense output initially. Do not label its learned sparse output as BM25; the BM25 baseline is a separate lexical method owned by Thiện.
- Define a chunking configuration shared across all text forms and coordinate it with Tài (transcripts), Thiện (retrieval), and Xuân Ngân (labels).
- Make a small diagnostic set of paraphrase, exact-match, multilingual (if included), and cross-source queries.
- Record model revision, tokenizer, embedding dimensions, normalization, vector distance operator, batch size, hardware, indexing time, and query latency.

## Technical work

- Implement a reproducible process for converting shared canonical chunks into dense vectors.
- Store or index vectors so each chunk can be filtered by authorized conversation and traced to a source and location.
- Implement top-k dense retrieval over the unified corpus, without using the gold source type as a query-time hint.
- Produce a stable result format with chunk ID, score, source ID, source type, and source location for evaluation.
- Verify that all four text-bearing source categories can be indexed; document any category-specific preprocessing limitations.

## Four-week checkpoints

### Week 1 — Model and interface

- Write the BGE-M3 model note and a concise comparison to a plausible alternative.
- Agree with Hao on chunk/result schemas and with Tài/Thiện/Xuân Ngân on shared data assumptions.

### Week 2 — Minimum dense-search demo

- Embed a small set of messages, PDF pages, and transcripts.
- Run fixed sample queries and inspect exact-match, paraphrase, and cross-source cases.
- Capture configuration, indexing cost, and latency.

### Week 3 — Controlled comparison

- Run dense retrieval on the same pilot corpus and questions used for BM25.
- Supply ranked outputs and settings to Xuân Ngân for the evaluator; coordinate candidate outputs with Thiện for the reranker.
- Analyze retrieval failures by source and question category.

### Week 4 — Findings and reproducibility

- Present the dense retrieval prototype and a model/configuration sheet.
- Summarize preliminary metrics and examples; separate observations from explanations that need more evidence.
- Ensure another teammate can reproduce a run from documented settings.

## Deliverables and acceptance checklist

- [ ] BGE-M3 selection note and bounded alternative-model comparison.
- [ ] Unified dense indexing and retrieval path that includes all four source categories.
- [ ] Source/location-preserving top-k result format that Xuân Ngân can score.
- [ ] Fixed configuration record and repeatable run instructions.
- [ ] Preliminary dense-search metrics and categorized success/failure examples.
- [ ] Latency and resource measurements appropriate to the prototype hardware.

## Handoffs and presentation segment

Give Thiện interchangeable candidate/result interfaces and dense top-k results for reranking; give Xuân Ngân ranked runs and exact configuration; give Tài the chunking rules for transcript experiments; give Hao model trade-offs, failure cases, and reproducibility notes. Your presentation section explains embeddings, dense similarity, the expected paraphrase benefit, and measured limitations.

## Risks to watch

- Using different chunks or queries for BM25 and dense comparisons.
- Giving the retriever the correct source category in advance during the unified-index experiment.
- Comparing results from incompatible model versions or vector settings.
- Dropping source IDs or locations when joining vector hits back to source records.
- Describing similarity scores as calibrated relevance probabilities.
