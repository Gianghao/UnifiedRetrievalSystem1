# Week 1 Meeting Preparation — Thiện (BM25, retrieval strategies, reranking)

Answers to my agenda questions, with the source and exact location for every claim that needs proof.
Design choices (tokenizer, top-k, timing plan, schema) are my proposals and need no citation.

## Q1. What should BM25 tokenize or normalize, and where is it strong?

**Answer**

- **Normalize:** convert all text to Unicode NFC first. Vietnamese accents can be stored two different ways, and without this the same word won't match itself. Then lowercase.
- **Keep:** accents, numbers, and codes like `INV-2024-0071`. Index the code both whole and split at the hyphens.
- **Skip for now:** stemming and stopword removal.
- **Settings:** start with k1 = 1.2 and b = 0.75 (the standard defaults). Do not tune them on the test questions.
- **Open decision:** split Vietnamese text by syllable (whitespace) or by word (a word segmenter)? Pick one and log it.
- **Where BM25 is strong:** exact identifiers, rare names, codes and dates. The evidence shows dense retrievers get worse as names get rarer, while BM25 barely cares how rare a name is.

**Proof**

- **Sciavolino et al., "Simple Entity-Centric Questions Challenge Dense Retrievers," EMNLP 2021** — <https://aclanthology.org/2021.emnlp-main.496.pdf>
  - §1 Introduction, Table 1 (proceedings p. 6138): dense retrieval "drastically underperforms the sparse BM25 baseline (49.7% vs 71.2% on average)" (top-20 accuracy).
  - §4 "Dissecting the Problem: Entities vs. Question Patterns", Figure 1 (p. 6140): "DPR performs well on the most common entities but quickly degrades on rarer entities, while BM25 is less sensitive to entity frequency."
  - Caveat: they tested DPR, not BGE-M3. It supports the pattern but does not prove it for our model.
- **Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," Foundations and Trends in IR 3(4), 2009, DOI 10.1561/1500000019** — <https://staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf>
  - §3.4, eq. 3.12–3.15 (pp. 359–360): the BM25 formula. "setting b = 1 will perform full document-length normalisation, while b = 0 will switch normalisation off."
  - §3.5 "Uses of BM25" (pp. 360–361): "values such as 0.5 < b < 0.8 and 1.2 < k1 < 2 are reasonably good in many circumstances. However, there is also evidence that optimal values do depend on other factors (such as the type of documents or queries)."
  - §5 "Parameter Optimisation" (p. 377): "the optimised parameters will be specific to the collection evaluated and may not work well for other collections." This supports not tuning on the test questions.
- **Elasticsearch reference, "Similarity module" page, section "BM25 similarity (default)"** — <https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html>
  - k1: "Controls non-linear term frequency normalization (saturation). The default value is 1.2."
  - b: "Controls to what degree document length normalizes tf values. The default value is 0.75."
- **Chen et al., "BGE M3-Embedding," arXiv 2402.03216** — <https://arxiv.org/abs/2402.03216>
  - §4.1 "Multi-Lingual Retrieval": the paper reports BM25 as a separate baseline next to its learned sparse output. This supports the rule that BGE-M3's sparse output must not stand in for BM25.

### Implementation plan

**Pilot (Weeks 1–4): in-memory BM25, no Postgres.** BM25 does the search and the ranking together. It scores every chunk that shares at least one word with the query, sorts by score, and keeps the top k.

- Robertson & Zaragoza §3.4 (p. 360): "the full document score is obtained by summing these term-weights over the (original or expanded) set of query terms."
- A chunk that shares no word with the query scores 0, so matching is built into the formula.
- A pilot of a few thousand chunks is small enough to score every chunk directly.

**Product (later): Postgres full-text search finds candidates, BM25 ranks them.** This adds speed through an inverted index, conversation-membership filtering where the data already lives, and live index updates. It gives the same results as plain BM25 if all four conditions hold:

1. **Postgres only finds matches; it does not rank.** Its built-in `ts_rank` / `ts_rank_cd` is not BM25 because it has no IDF.
   - PostgreSQL docs §12.3.3 "Ranking Search Results": "It is important to note that the ranking functions do not use any global information." <https://www.postgresql.org/docs/current/textsearch-controls.html>
2. **Match with OR, not AND.** `plainto_tsquery` requires every word to be present. That drops chunks BM25 would still have ranked, so the condition is no longer a BM25 baseline. Build the tsquery with `|`.
   - Same page, §12.3.2 "Parsing Queries": in `plainto_tsquery`, "the & (AND) tsquery operator is inserted between surviving words."
   - With OR, Postgres returns exactly the chunks that get a BM25 score above 0.
3. **IDF and avgdl come from the whole corpus, not from the matched rows.**
   - Document frequency per word comes from `ts_stat(...)`, column `ndoc`. PostgreSQL docs §12.4.4 "Gathering Document Statistics": `ndoc` is the "number of documents (tsvectors) the word occurred in." <https://www.postgresql.org/docs/current/textsearch-features.html>
   - Chunk length: `length(tsvector)` "Returns the number of lexemes", which counts distinct words, not total words (PostgreSQL docs §9.13, Table 9.43). Either a stored token count or the distinct-word count is acceptable. Robertson & Zaragoza §3.4 (p. 359) say "the number of unique terms" gives "very similar results". Log which one is used.
4. **Use the same text processing in every condition.** Use the `simple` config (lowercase, no stemming), with NFC normalization done before indexing.

**Alternative:** use a Postgres BM25 extension (Tiger Data `pg_textsearch`, ParadeDB `pg_search`, VectorChord-bm25). Each one adds a dependency, and their tokenizers would need checking on Vietnamese. Not needed for the pilot.

## Q2. What supports BGE-reranker-v2-m3, and what does it cost to run?

**Answer**

- **Why this model:** it is built on BGE-M3, the same model family as Quân's dense search. It is multilingual, Apache-2.0 licensed, and about 0.6B parameters.
- **Why rerank only a short list:** a cross-encoder reads the question and each candidate together. That makes it more accurate but slow, so it can only run on a short candidate list.
- **Cost:** there is no published latency figure. I measured it on this Mac; see the benchmark under Q3. With 50 long chunks it takes about 4.3–4.6 s per query; with 50 short messages, about 0.4 s.
- **Vietnamese:** the model card says "multilingual", but I found no Vietnamese-specific reranking score. This is still uncertain. Or consider to switch to ViReranker when Vietnamese is detected.

**Proof**

- **Hugging Face model card, BAAI/bge-reranker-v2-m3** — <https://huggingface.co/BAAI/bge-reranker-v2-m3>
  - Header metadata: "0.6B params", "License: apache-2.0".
  - "Model List" table: base model bge-m3, language "Multilingual".
  - "Usage → Using FlagEmbedding → For normal reranker": "Setting use_fp16 to True speeds up computation with a slight performance degradation."
  - "Usage → Using Huggingface transformers → For normal reranker": the example uses `max_length=512`.
- **Sentence-Transformers docs, "Retrieve & Re-Rank"** — <https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html>
  - Section "Re-Ranker: Cross-Encoder": "The advantage of Cross-Encoders is the higher performance, as they perform attention across the query and the document." / "Scoring thousands or millions of (query, document)-pairs would be rather slow." / "we use the retriever to create a set of e.g. 100 possible candidates which are then re-ranked by the Cross-Encoder."
- **Thakur et al., "BEIR," NeurIPS 2021 Datasets and Benchmarks Track** — <https://arxiv.org/abs/2104.08663>
  - Abstract: "re-ranking and late-interaction-based models on average achieve the best zero-shot performances … at high computational costs." The same abstract says "BM25 is a robust baseline."

## Q3. Does dense top-50 → rerank-to-top-10 fit our hardware and time?

**Answer**

- **Memory: yes (measured).** BGE-M3 and the reranker loaded together on the Mac's GPU (MPS) use 4.3 GB in fp16 and 6.3 GB in fp32, out of 16 GB.
- **Time: OK for offline experiments, too slow for live chat at 50 long candidates.**
  - Dense top-50 → rerank → top-10 takes **4.3 s p50 / 4.9 s p95** per query. Almost all of it is the reranker; candidate search takes only 26 ms.
  - A 30-question pilot run takes about 2.5 minutes, which is fine for the experiment.
- **Proposed cutoffs:** BM25 top-10; dense top-10; dense top-50 → rerank → top-10. Keep 50 for the experiment, and also report top-20 so the latency cost is visible.

### Benchmark (measured 2026-11-12)

**Setup**

- **Machine:** Apple M4, 16 GB RAM, PyTorch 2.15 on MPS.
- **Models:** `BAAI/bge-m3` (dense, 1024-dim) and `BAAI/bge-reranker-v2-m3`, reranker max_length 512.
- **Corpus:** synthetic Vietnamese, with 1,000 short chunks (chat-message size, median 22 tokens) and 1,000 long chunks (PDF page or transcript size, median 392 tokens).
- **Runs:** 3 warm-up queries, then 30 measured queries.
- **Files:** script `agenda-bench/bench.py`, raw output `agenda-bench/bench_result.json`.

| Step | p50 | p95 |
| :--- | ---: | ---: |
| BM25 search, top-10 (in memory, 2,000 chunks) | 1.3 ms | 1.5 ms |
| Dense query encode + search, top-50 | 20.5 ms | 22.5 ms |
| Rerank 20 short chunks (fp16) | 0.17 s | 0.19 s |
| Rerank 50 short chunks (fp16) | 0.40 s | 0.44 s |
| Rerank 20 long chunks (fp16) | 1.81 s | 1.91 s |
| Rerank 30 long chunks (fp16) | 2.73 s | 2.92 s |
| Rerank 50 long chunks (fp16) | 4.61 s | 4.98 s |
| Rerank 50 long chunks (fp32) | 5.53 s | 5.92 s |
| Rerank 50 long chunks (CPU only, fp32) | 13.2 s | 15.9 s |
| **End-to-end dense top-50 → rerank → top-10 (fp16):** `t_candidate` | 26 ms | 48 ms |
| `t_rerank` | 4.30 s | 4.88 s |
| `t_total` | 4.33 s | 4.90 s |

Indexing: BM25 builds in 0.08 s; BGE-M3 embeds 2,000 chunks in 92 s.

**Findings**

1. **Reranker time grows with candidate count × chunk length.** Long chunks cost about 11× more than short messages for the same count. The cutoff decision depends on chunk size, which is a dependency on Quân's chunking.
2. **One long chunk slows down the whole batch.** Dense top-50 from the mixed corpus took 4.2 s p50, almost as slow as all-long chunks, because every pair in a batch is padded to the longest one. Sorting candidates by length into separate batches should help. Test it in Week 2.
3. **fp16 is about 15–20% faster than fp32, and the GPU is about 3× faster than CPU.** The model card warns fp16 causes "slight performance degradation", so check ranking quality before choosing fp16.
4. **BM25 and dense search are negligible next to reranking.**

**Limits**

- This measures speed only, not quality; there are no relevance labels yet.
- The text is synthetic and template-based. Latency depends on token count, not content, so the timings should carry over.
- One machine, one run, with other apps open.

**BM25 library note:** `rank_bm25`'s `BM25Okapi` computes IDF as log((N−df+0.5)/(df+0.5)) (`rank_bm25.py` line 96). For any word found in half the chunks or more, this is 0 or negative, and the library replaces it with a small floor value. For the real baseline, use the Lucene form ln(1 + (N−df+0.5)/(df+0.5)), or `bm25s` with `method="lucene"`, and log the choice. This does not affect the latency numbers.

## Q4. How will candidate recall, reranking latency and end-to-end latency be reported separately?

**Answer** (method design, no citation needed)

- **Three timers per query:**
  - `t_candidate`: encoding the query plus the vector search.
  - `t_rerank`: the cross-encoder only.
  - `t_total`: everything.
- **Report p50 and p95, not the average.** Use warm runs on the same hardware, and log the configuration with the results.
- **Two recall numbers:** Recall@50 of the dense candidates (was the evidence in the list at all?) and Recall@10 after reranking.
- **Sort each failure into one of two kinds:**
  - Evidence not in the top 50: a candidate-generation failure (Quân's side).
  - Evidence in the top 50 but not in the final top 10: a reranking failure (my side).

## Q5. Should hybrid retrieval stay optional until the three primary conditions work?

**Answer**

- Yes. The pilot is only 20–30 questions, which is too few to claim hybrid helps.
- If it is run, use Reciprocal Rank Fusion (RRF) with k = 60. It needs no tuning, which matters because there is no separate set of questions to tune on.

**Proof**

- **Cormack, Clarke & Büttcher, "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods," SIGIR 2009** — <http://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf>
  - §1 "Reciprocal Rank Fusion" (p. 1): RRFscore(d) = Σ 1/(k + r(d)), "where k = 60 was fixed during a pilot investigation and not altered during subsequent validation."
  - p. 1, describing Table 1 (Table 1 is on p. 2): "k = 60 was near-optimal, but that the choice was not critical."

## Interface proposal (agenda slot 50–65 min)

This is a proposal to agree with Hao, Quân, Tài and Xuân Ngân.

- **Chunk fields:** `chunk_id`, `conversation_id`, `source_id`, `source_type`, `location` (a page, start/end ms, or a message time) and `text`.
- **Result fields:** `run_id`, `query_id`, `method`, `rank`, `chunk_id`, `score`, `candidate_rank` (the rank before reranking), `t_candidate`, `t_rerank` and `t_total`.
- **Rule:** `source_type` is never given to retrieval as an input.

## Verification status

- **Checked against the PDF text:** the quotes and page numbers for Robertson & Zaragoza, Sciavolino and Cormack. The Sciavolino Figure 1 page number was worked out from where it sits in the PDF.
- **Read through a summarizer:** the quotes from the model card, Sentence-Transformers docs, Elasticsearch docs and the BEIR and BGE-M3 abstracts. Open each one once before putting it on a slide.
- **Measured on this Mac:** all latency and memory numbers under Q3 (synthetic corpus).
- **Not measured yet:** ranking quality for any method, the effect of fp16 on rerank quality, and ViRanker (`namdp-ptit/ViRanker`, fine-tuned from bge-m3). ViRanker has the same architecture, so its speed should be about the same.
