# Retrieval Strategies Benchmark — Thiện (BM25, dense, reranking, hybrid)

Preliminary comparison of five retrieval strategies on **synthetic data with planted answers**.
These numbers show how the strategies differ; they are not final accuracy claims. The real test needs
Xuân Ngân's annotated question set.

- **Strategies:** `bm25` (pg_textsearch), `dense` (BGE-M3), `dense50_rerank10` (dense top-50 → bge-reranker-v2-m3 → top-10), `hybrid_rrf` (BM25 50 + dense 50 → RRF → top-10), `hybrid_rrf50_rerank10` (RRF top-50 → reranker → top-10).
- **Datasets:** (a) **chat**: new realistic Vietnamese chat corpus (`chat_dataset.py`), 146 scored queries (130 answerable + 16 unanswerable) in 9 types; (b) **synthetic**: the first dataset, 55 queries in 3 types.
- **Sizes:** 10k chunks (one conversation) and 1M chunks (whole corpus). About 5% of chunks are ~300-word chunks standing in for PDF pages and transcript windows; the rest are one-line messages.
- **Hardware:** NVIDIA L4 (22.5 GB) on Colab for all main results. Apple M4 (MPS) only for the old synthetic 10k run (section 7).
- **Nothing was tuned.** All settings are defaults (candidate_k 50, top_k 10, rrf_k 60, reranker max_len 512).
- **Run notes:** G4 was requested first, but Colab returned errors for about 10 minutes and A100 was unavailable, so everything ran on L4. Bugs found and fixed during the runs: an fp16/fp32 dtype mismatch in the GPU search, and an embedding cache keyed only by size, so one chat 10k run silently reused synthetic embeddings. That run was discarded and redone; the cache is now keyed by dataset too.

## 1. Summary (chat dataset, 1M chunks, L4)

Quality is over the 130 answerable queries. Latency is per query, total.

| Strategy | Recall@10 | MRR@10 | nDCG@10 | p50 | p95 | Strong at | Weak at |
|---|---|---|---|---|---|---|---|
| **BM25** | 0.715 | 0.622 | 0.646 | **6.2 ms** | **15.9 ms** | Exact codes (1.000), code-switch (1.000) | Long-chunk facts (0.188), no-diacritics (0.062) |
| **Dense** | 0.677 | 0.581 | 0.606 | 36.9 ms | 38.2 ms | Paraphrase (0.875 / 0.875) | Vague context (0.375), exact codes (0.778) |
| **Dense → rerank** | 0.708 | 0.621 | 0.643 | 62.9 ms | 380.1 ms | Long-chunk facts (0.688) | Vague context (0.375), no-diacritics (0.062) |
| **Hybrid RRF** | **0.785** | 0.636 | 0.673 | 43.5 ms | 52.5 ms | Vague context (0.750), teencode (0.938) | Order of long-chunk hits (MRR 0.396) |
| **Hybrid RRF → rerank** | 0.769 | **0.676** | **0.700** | 73.1 ms | 394.5 ms | Long-chunk (0.688), vague context (0.750 / 0.698) | No-diacritics (0.125), paraphrase order (MRR 0.778) |

Same strategies on **chat 10k** (conversation-sized):

| Strategy | Recall@10 | MRR@10 | nDCG@10 | p50 | p95 |
|---|---|---|---|---|---|
| BM25 | 0.792 | 0.652 | 0.686 | 0.7 ms | 0.9 ms |
| Dense | 0.769 | 0.670 | 0.695 | 20.8 ms | 21.8 ms |
| Dense → rerank | 0.838 | 0.761 | 0.781 | 48.9 ms | 382.4 ms |
| Hybrid RRF | 0.823 | 0.676 | 0.713 | 21.2 ms | 22.5 ms |
| **Hybrid RRF → rerank** | **0.885** | **0.797** | **0.820** | 52.9 ms | 396.6 ms |

**In one line:** hybrid candidates → rerank has the best ordering at both sizes (MRR 0.797 at 10k,
0.676 at 1M), and hybrid RRF without reranking has the best recall at 1M (0.785). Dense alone is the
weakest at 1M. Two problems remain for every strategy: queries without accents (≤ 0.250 recall) and
corrections (the outdated message ranks first).

## 2. Quality by question type (chat dataset)

Recall@10 / MRR@10. Types: `exact_code` asks for a document number or code. `paraphrase` uses different
words from the answer. `long_chunk_fact` hides the answer inside a ~300-word chunk. `no_diacritics`
has accents stripped on one side (query or message), so the two sides do not match literally.
`code_switch` mixes English and Vietnamese. `teencode` uses slang spellings (ko, đc, j...).
`vague_context` refers to things loosely ("ổng gửi cái file logo hôm bữa chưa"). `correction` has an old
message and a later correction; the correction is the gold. `unanswerable` has no answer (not scored here, see 3.3).

**1M chunks**

| Type (n) | BM25 | Dense | Dense → rerank | Hybrid RRF | Hybrid → rerank |
|---|---|---|---|---|---|
| exact_code (18) | **1.000 / 0.972** | 0.778 / 0.585 | 0.833 / 0.741 | 0.944 / 0.869 | 0.889 / 0.824 |
| paraphrase (16) | 0.938 / 0.849 | 0.875 / 0.875 | 0.938 / 0.841 | 0.938 / 0.896 | 0.875 / 0.778 |
| long_chunk_fact (16) | 0.188 / 0.046 | 0.625 / 0.594 | **0.688 / 0.688** | 0.625 / 0.396 | **0.688 / 0.688** |
| no_diacritics (16) | 0.062 / 0.062 | 0.062 / 0.021 | 0.062 / 0.062 | 0.125 / 0.073 | 0.125 / 0.125 |
| code_switch (16) | **1.000 / 1.000** | 0.938 / 0.938 | 0.938 / 0.938 | 0.938 / 0.938 | 0.938 / 0.938 |
| teencode (16) | 0.875 / 0.875 | 0.812 / 0.812 | 0.875 / 0.780 | **0.938 / 0.854** | 0.875 / 0.779 |
| vague_context (16) | 0.625 / 0.562 | 0.375 / 0.333 | 0.375 / 0.375 | **0.750** / 0.493 | **0.750 / 0.698** |
| correction (16) | 1.000 / 0.562 | 0.938 / 0.490 | 0.938 / 0.531 | 1.000 / 0.537 | 1.000 / 0.562 |
| **all answerable (130)** | 0.715 / 0.622 | 0.677 / 0.581 | 0.708 / 0.621 | **0.785** / 0.636 | 0.769 / **0.676** |

**10k chunks**

| Type (n) | BM25 | Dense | Dense → rerank | Hybrid RRF | Hybrid → rerank |
|---|---|---|---|---|---|
| exact_code (18) | 1.000 / 0.963 | 0.833 / 0.806 | 0.944 / 0.917 | 0.889 / 0.852 | 0.944 / 0.917 |
| paraphrase (16) | 1.000 / 0.871 | 1.000 / 1.000 | 1.000 / 0.953 | 1.000 / 0.953 | 1.000 / 0.953 |
| long_chunk_fact (16) | 0.312 / 0.127 | 0.812 / 0.684 | 0.812 / 0.812 | 0.688 / 0.322 | **0.938 / 0.938** |
| no_diacritics (16) | 0.125 / 0.075 | 0.062 / 0.062 | 0.188 / 0.188 | 0.188 / 0.104 | 0.250 / 0.250 |
| code_switch (16) | 1.000 / 1.000 | 0.938 / 0.938 | 0.938 / 0.938 | 1.000 / 0.953 | 0.938 / 0.938 |
| teencode (16) | 1.000 / 0.913 | 0.875 / 0.875 | 1.000 / 0.927 | 0.938 / 0.906 | 1.000 / 0.927 |
| vague_context (16) | 0.875 / 0.663 | 0.625 / 0.460 | 0.812 / 0.771 | 0.875 / 0.735 | **1.000 / 0.880** |
| correction (16) | 1.000 / 0.562 | 1.000 / 0.521 | 1.000 / 0.562 | 1.000 / 0.562 | 1.000 / 0.562 |
| **all answerable (130)** | 0.792 / 0.652 | 0.769 / 0.670 | 0.838 / 0.761 | 0.823 / 0.676 | **0.885 / 0.797** |

## 3. Findings specific to chat

### 3.1 No-diacritics queries fail for every strategy

Best recall at 1M is 0.125 (hybrid, with or without rerank). At 10k the best is 0.250
(hybrid → rerank). Two reasons:

- The Postgres `simple` text config only lowercases and splits. It keeps accents, so `khau` does not
  match `khẩu`. BM25 gets 0.062 at 1M.
- BGE-M3 is also weak on this: dense gets 0.062 at both sizes. Reranking only helps when the answer
  is already a candidate, and candidate recall@50 is just 0.062 (dense, BM25) and 0.125 (RRF) at 1M.

### 3.2 Corrections: the outdated message comes first

Recall@10 is 1.000 for BM25, hybrid RRF and hybrid → rerank at 1M, so the correction is found. But in
**14 of 16** correction queries the outdated message is ranked above the correction (hybrid → rerank,
both 10k and 1M; same 14/16 for BM25, dense → rerank and hybrid RRF; dense alone 15/16). That is why
MRR is only 0.490–0.562 for this type at 1M. Retrieval has no notion of time. A reader who takes the
top result gets the wrong answer.

### 3.3 Unanswerable queries: a score threshold is not enough

The reranker's top-1 score separates the medians but the distributions overlap. Threshold 0:

| Run | Answerable with top-1 below 0 (wrongly abstain) | Unanswerable with top-1 at or above 0 (wrongly answer) | Median top-1 (answerable / unanswerable) |
|---|---|---|---|
| 10k hybrid → rerank | 26 / 130 | 3 / 16 | 3.298 / -2.789 |
| 10k dense → rerank | 30 / 130 | 3 / 16 | 3.052 / -2.789 |
| 1M hybrid → rerank | 28 / 130 | 2 / 16 | 3.048 / -1.894 |
| 1M dense → rerank | 31 / 130 | 2 / 16 | 3.022 / -1.754 |

At threshold 0, about one in five answerable queries would get "no answer", and a few unanswerable ones
would still get one.

### 3.4 Vague context: dense is weak, hybrid helps

At 1M, dense gets 0.375 recall and dense → rerank also 0.375. BM25 gets 0.625. Hybrid gets 0.750, and
hybrid → rerank keeps 0.750 with the best order (MRR 0.698). Candidate recall@50 shows why: dense 0.438,
BM25 0.750, RRF 0.812. The dense candidates miss the answer, so the reranker cannot fix it.

### 3.5 Exact codes: BM25 is strongest, dense drops at 1M

BM25 keeps 1.000 recall at 1M (0.972 MRR). Dense falls from 0.833 (10k) to 0.778 (1M), and
dense → rerank from 0.944 to 0.833. Hybrid RRF holds at 0.944 and hybrid → rerank at 0.889.
Note: hybrid → rerank is a little below BM25 alone here, because the reranker re-orders some
exact-code hits.

### 3.6 Follow-up: accent folding for BM25 (`unaccent`)

Rerun of the chat dataset with BM25 using a `simple_unaccent` config (Postgres `unaccent`, applied at
index and query time: `Mật khẩu wifi đã gửi` → `mat khau wifi da gui`). Dense is unchanged (identical
numbers). Same L4, same queries. Files: `colab_chat_unaccent_10k.json`, `colab_chat_unaccent_1m.json`.

Recall@10 / MRR@10, **1M chunks**, `simple` → `simple_unaccent`:

| Type (n) | BM25 | Hybrid RRF | Hybrid → rerank |
|---|---|---|---|
| no_diacritics (16) | 0.062 / 0.062 → **1.000 / 1.000** | 0.125 / 0.073 → **1.000 / 0.686** | 0.125 / 0.125 → **1.000 / 1.000** |
| paraphrase (16) | 0.938 / 0.849 → 0.688 / 0.634 | 0.938 / 0.896 → 0.875 / 0.781 | 0.875 / 0.778 → 0.875 / 0.778 |
| code_switch (16) | 1.000 / 1.000 → 0.688 / 0.688 | 0.938 / 0.938 → 0.938 / 0.823 | 0.938 / 0.938 → 0.938 / 0.938 |
| vague_context (16) | 0.625 / 0.562 → 0.375 / 0.375 | 0.750 / 0.493 → 0.562 / 0.398 | 0.750 / 0.698 → 0.500 / 0.469 |
| long_chunk_fact (16) | 0.188 / 0.046 → 0.000 / 0.000 | 0.625 / 0.396 → 0.625 / 0.354 | 0.688 / 0.688 → 0.688 / 0.688 |
| **all answerable (130)** | 0.715 / 0.622 → 0.700 / 0.634 | 0.785 / 0.636 → **0.854 / 0.666** | 0.769 / 0.676 → **0.846 / 0.756** |

At **10k**, all answerable: BM25 0.792 / 0.652 → 0.800 / 0.682; hybrid RRF 0.823 / 0.676 → 0.846 / 0.677;
hybrid → rerank 0.885 / 0.797 → **0.962 / 0.879**.

- **It fixes no-diacritics completely** (BM25 0.062 → 1.000 at 1M).
- **It hurts BM25 on accented queries.** Vietnamese words that differ only by accent now collide
  (má / mã / mà, đá / da), so BM25 pulls in wrong matches: paraphrase, code_switch and vague_context drop
  by 0.250–0.312 at 1M. BM25 alone is about flat overall (0.715 → 0.700).
- **In hybrid it is a clear win overall,** because dense still covers the accented cases: hybrid → rerank
  goes 0.769 → 0.846 recall and 0.676 → 0.756 MRR at 1M. The vague_context drop (0.750 → 0.500) is the cost.
- **Latency:** BM25 at 1M p50 6.2 → 12.3 ms (more chunks match once accents are gone). Hybrid → rerank total
  p50 73.1 → 77.9 ms.
- Corrections are unchanged (stale still first in 14/16).
- **Next to test (not run):** keep both forms instead of choosing one, e.g. use the accented index when the
  query has accents and the unaccented index when it has none, or fuse both BM25 lists in RRF.
- Implementation note: pg_textsearch only finds a custom text search config when it is schema-qualified
  (`text_config='public.simple_unaccent'`).

## 4. Scale effect: 10k → 1M

Change in Recall@10 / MRR@10 (negative = worse at 1M).

| Strategy | Chat Recall | Chat MRR | Synthetic Recall | Synthetic MRR |
|---|---|---|---|---|
| BM25 | -0.077 | -0.030 | -0.036 | -0.012 |
| Dense | -0.092 | -0.089 | -0.073 | -0.055 |
| Dense → rerank | **-0.130** | **-0.140** | -0.091 | -0.103 |
| Hybrid RRF | -0.038 | -0.040 | **-0.018** | -0.020 |
| Hybrid → rerank | -0.116 | -0.121 | **-0.109** | **-0.121** |

- **Rerank pipelines lose the most**, because 100 times more distractors push the answer out of the
  top-50 candidates before the reranker sees it. Hybrid RRF without rerank loses the least.
- Even after the drop, hybrid → rerank is still best on MRR at 1M for both datasets (0.676 chat, 0.806 synthetic).
- Latency barely changes for dense (36.9 ms at 1M vs 20.8 ms at 10k on chat), since exact GPU search is cheap.
  BM25 goes from 0.7 to 6.2 ms.

## 5. Candidate miss vs. reranking

Candidate recall@50 is the most a reranker can reach.

| Candidates from | Chat 1M | Synthetic 1M | Chat 10k | Synthetic 10k |
|---|---|---|---|---|
| Dense top-50 | 0.723 | 0.727 | 0.846 | 0.818 |
| BM25 top-50 | 0.754 | 0.618 | 0.846 | 0.764 |
| RRF (BM25 + dense) top-50 | **0.815** | **0.818** | **0.900** | **0.927** |
| *Actual hybrid → rerank Recall@10* | *0.769* | *0.818* | *0.885* | *0.927* |

- RRF candidates are better than either source alone at all four settings. This confirms the earlier
  guess that hybrid candidates lift the reranker's ceiling.
- On synthetic data the reranker reaches the ceiling (0.818 and 0.927). On chat it falls a bit short
  (0.769 of 0.815 at 1M, 0.885 of 0.900 at 10k): a few answers are in the candidates but ranked below 10.
- The largest gap is still candidate generation. Most misses happen before the reranker sees the answer.

## 6. Latency breakdown (chat, L4, per query, ms)

| Strategy | Stage | 10k p50 / p95 | 1M p50 / p95 |
|---|---|---|---|
| BM25 | total | 0.7 / 0.9 | 6.2 / 15.9 |
| Dense | total | 20.8 / 21.8 | 36.9 / 38.2 |
| Dense → rerank | candidates | 20.3 / 21.4 | 36.5 / 37.9 |
| | rerank 50 → 10 | 29.0 / 360.9 | 26.7 / 342.5 |
| | **total** | 48.9 / 382.4 | 62.9 / 380.1 |
| Hybrid RRF | BM25 part | 0.8 / 1.1 | 6.7 / 16.3 |
| | dense part | 20.3 / 21.4 | 36.5 / 37.9 |
| | **total** | 21.2 / 22.5 | 43.5 / 52.5 |
| Hybrid → rerank | candidates | 21.2 / 22.5 | 43.5 / 52.5 |
| | rerank 50 → 10 | 31.6 / 373.2 | 28.1 / 347.6 |
| | **total** | 52.9 / 396.6 | 73.1 / 394.5 |

The reranker's p95 is about 12 times its p50: when the 50 candidates include long chunks it is slow.
Hybrid adds 6.6 ms (p50) over dense at 1M, before reranking.

## 7. Hardware: Apple M4 vs. NVIDIA L4 (synthetic, 10k, same run)

Quality is identical on both machines for the four strategies that ran on both (BM25 0.600, dense 0.800,
dense → rerank 0.818, hybrid RRF 0.800 Recall@10). Only speed differs.

| Measure | M4 (MPS) | L4 (CUDA) |
|---|---|---|
| Dense total p50 / p95 | 35.5 / 50.4 ms | 20.7 / 22.0 ms |
| Dense → rerank: rerank stage p50 / p95 | 377.7 / 5,035.0 ms | 29.2 / 465.0 ms |
| Dense → rerank: total p50 / p95 | 411.4 / 5,065.2 ms | 49.5 / 485.1 ms |
| Hybrid RRF total p50 / p95 | 33.9 / 37.0 ms | 21.3 / 22.4 ms |
| BM25 total p50 / p95 | 0.6 / 1.0 ms | 0.9 / 1.2 ms |
| Embed 10k chunks | 105.9 s | 9.7 s (chat 10k run; the synthetic 10k L4 run reused cached embeddings) |

- The rerank stage p95 is about **10.8 times** lower on L4 (5,035.0 → 465.0 ms). The 5 s p95 seen on the laptop was mostly hardware.
- **Embedding 1M chunks on L4:** 1,132.6 s (synthetic) and 933.0 s (chat). The M4 estimate was about 3 hours
  (not run).
- BM25 runs on the database, not the GPU. The small difference there is a different Postgres host, not the GPU.
- **Colab cost:** 100 compute units at the start, 98.24 at the end. About 1.76 units for all four L4 runs, at a rate of about 1.94 units/hour.

## 8. BM25 at large scale (1M chunks)

Separate test (`bm25_scale_bench.py`). Same BM25 formula everywhere, so the methods return the
same top-10. Only speed differs.

| BM25 method | Whole corpus, 1M chunks (p50 / p95) | One conversation, ~1k chunks (p50 / p95) | Same top-10 scores as brute force |
|---|---|---|---|
| Brute force (score every chunk) | 2,633 / 3,205 ms | **7.5 / 8.7 ms** | baseline |
| Full-text search (GIN) + BM25 | 1,530 / 1,854 ms | 45 / 55 ms | 30 / 30 |
| **pg_textsearch** BM25 index | **15 / 27 ms** | 67 / 109 ms | 29 / 30 |

- Full-text search alone barely helps. With syllable tokens, a typical query matches **28%** of all chunks.
- pg_textsearch is ~170× faster on the whole corpus, but slower inside one conversation, because it
  filters by conversation after ranking.
- pg_textsearch stores chunk lengths approximately (exact up to 39 tokens, up to ~6% off above
  that). This caused the 1/30 mismatch on long chunks.

## 9. What this means (preliminary)

1. **Hybrid candidates → rerank is the best overall for ordering.** Best MRR and nDCG at both sizes on chat,
   and RRF candidates have the highest overall candidate recall@50 in every run (per type, dense candidates
   still win on paraphrase at 1M: 1.000 vs 0.938). p95 is about 395 ms on L4, fine for chat.
   If recall alone matters, plain hybrid RRF is cheaper (52.5 ms p95 at 1M) and has the best Recall@10 at 1M.
2. **Do not use dense alone** for chat data. On chat at 1M it is last on Recall@10, MRR and nDCG, and loses
   on exact codes and vague context.
3. **Use accent folding for BM25 inside hybrid** (tested, section 3.6): no-diacritics goes to 1.000 and hybrid
   → rerank improves to 0.846 recall / 0.756 MRR at 1M, but BM25 alone gets worse on accented queries. Next:
   choose the index by whether the query has accents, or fuse both BM25 lists.
4. **Corrections need time information.** Store message timestamps and test preferring the newest message when
   two results are near-duplicates. Today the stale message ranks first in 14/16 cases even though it is
   not missed. The synthetic chats have no timestamps, so this needs a dataset that has them.
5. **Abstention needs more than a reranker score threshold.** At threshold 0, 26–31 of 130 answerable
   queries would be refused and 2–3 of 16 unanswerable would still be answered. Test a calibrated threshold per
   corpus size plus other signals.
6. **Long documents need a chunking decision.** BM25 alone gets 0.188 on long-chunk facts at 1M; only rerank
   pipelines reach 0.688. Discuss chunk size for PDFs and transcripts with Quân.
7. **GPU matters for the reranker.** On L4 the rerank stage p95 is under 0.5 s; on M4 it was about 5 s.
   The deployment target decides if reranking is usable.

## 10. Limitations

- **Synthetic data and labels.** Questions were written by us and one answer is planted for each. Real chat is
  messier and many questions need more than one piece of evidence. With one gold chunk per query,
  Complete Evidence@10 equals Recall@10, so it is not reported separately.
- **Rare planted names make BM25 easier.** Gold chunks use reserved rare names, brands and codes that filler never uses.
  Real data will have more collisions.
- **One message = one chunk.** No sliding windows or merging of replies.
- **Single-speaker chats, no timestamps.** Corrections are tested only by order, not by time.
- **Small samples.** 130 answerable queries; 16 per type (18 for exact_code), so **one query is about 6 points
  within a type**. No confidence intervals. Differences of one or two queries are noise.
- **L4, not G4 or A100.** Latency on the real deployment GPU will differ.
- **Defaults only, nothing tuned.** No tuning of candidate_k, rrf_k, tokenizer or reranker length.
- **Dense search ran in memory** (exact GPU search), not in pgvector as the app would. Embedding the query dominates.
- **Tokenizer:** Postgres `simple` (lowercase, split by syllable, no stop words). It splits
  `HD-2024-0001` into `hd`, `-2024`, `-0001`.
- **Hybrid ran BM25 and dense one after the other.** Running them in parallel would be slightly faster.
- **Earlier synthetic exact-code test was too easy** (dense also scored 1.000 on it); the chat dataset's
  exact_code type is harder (dense 0.778 at 1M).

## 11. Reproduce

Files in `agenda-bench/`:

| File | What |
|---|---|
| `strategies_bench.py` | The benchmark (5 strategies; `DATASET=chat` or synthetic) |
| `chat_dataset.py` | Synthetic Vietnamese chat corpus and 9 query types (all names and codes invented) |
| `strategies_bench_colab.ipynb` | Colab notebook that runs the benchmark on a GPU |
| `strategies_result.json` | Old run: M4, synthetic 10k, 4 strategies (no hybrid → rerank) |
| `colab_result_10k.json`, `colab_result_1m.json` | L4, synthetic, 10k and 1M, 5 strategies |
| `colab_chat_result_10k.json`, `colab_chat_result_1m.json` | L4, chat dataset, 10k and 1M, 5 strategies |
| `colab_chat_unaccent_10k.json`, `colab_chat_unaccent_1m.json` | Same, with `BM25_CONFIG=simple_unaccent` (section 3.6) |
| `bm25_scale_bench.py`, `bm25_scale_result.json` | 1M-chunk BM25 test (section 8) |
| `Dockerfile.pg17-bm25` | Postgres 17 + pg_textsearch 1.5.1 |

All JSONs include the rank of the gold chunk for every query (`per_query`).

```sh
cd agenda-bench
docker build -t bm25-bench:pg17 -f Dockerfile.pg17-bm25 .
docker run -d --name bm25-bench -p 55434:5432 -e POSTGRES_PASSWORD=bench --shm-size=2g bm25-bench:pg17 \
  postgres -c shared_preload_libraries=pg_textsearch -c shared_buffers=2GB -c maintenance_work_mem=2GB -c work_mem=256MB
pip install "psycopg[binary]" torch sentence-transformers transformers numpy
python strategies_bench.py > strategies_result.json                 # synthetic, 10k, ~10 min on an M4
DATASET=chat python strategies_bench.py > colab_chat_result_10k.json # chat dataset
python bm25_scale_bench.py > bm25_scale_result.json                 # ~15 min
```

For the 1M runs and the L4 results, use `strategies_bench_colab.ipynb`. It runs the same script. Its run cells set `N_CHUNKS`; for the chat dataset, also upload `chat_dataset.py`
and prefix the run command with `DATASET=chat`, e.g. `!DATASET=chat N_CHUNKS=1000000 EMB_CACHE=/content/emb_cache_chat python strategies_bench.py > chat_1m.json`.
