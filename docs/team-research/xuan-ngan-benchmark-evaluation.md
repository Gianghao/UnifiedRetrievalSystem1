# Xuân Ngân — Benchmark, Evidence Annotation, and Evaluation Researcher

**Team role:** Member 5 in the research proposal  
**Primary ownership:** Define the benchmark and evidence labels that make the system's retrieval claims measurable. Your research and product-development strengths support a rigorous protocol that is also clear and usable by the team.

## Mission

Create a small, defensible evaluation set for the four source categories, implement or coordinate reproducible scoring, and make cross-source evidence completeness a first-class outcome. The initial target is approximately 20–30 manually annotated questions for a proof of concept; label it as a pilot rather than a final benchmark.

## Questions to investigate

1. What counts as a relevant passage, a required evidence group, and an acceptable alternative passage?
2. How can annotation consistency be checked when a question needs multiple sources to answer completely?
3. How should answerable and unanswerable questions be represented and scored?
4. Which metrics reveal ranking quality, evidence completeness, and whether the reranker received the needed evidence?
5. How should results be separated by source type, single-source/cross-source category, and query type?
6. How can answer faithfulness and source attribution be assessed without conflating them with retrieval quality?

## Research tasks

- Study nDCG@10, Recall@10, Complete Evidence@10, MRR@10, Candidate Recall@50, p50/p95 latency, WER, and answer faithfulness. Specify the unit and denominator for every metric.
- Write annotation guidelines and test them on a few examples before labeling the full pilot.
- Create examples for message, PDF page, audio time range, video time range, and multi-source evidence.
- For cross-source questions, define evidence groups so success requires coverage of every required group; accept legitimate alternative passages that establish the same fact.
- Include unanswerable questions and state how they are evaluated; do not force an answer when the corpus lacks support.
- Split questions or sources into development and held-out subsets where feasible. State that a 20–30 item pilot has limited statistical power and supports exploratory observations only.
- Coordinate a second-person review of a sample of labels; log disagreements and the resolution rule.
- For the secondary answer experiment, compare the same fixed generator/prompt/configuration using gold evidence versus retrieved evidence, and review a human-labeled subset.

## Technical work

- Build a machine-readable dataset with question IDs, question text, answerability, category, required evidence groups, acceptable alternatives, source IDs, and source locations.
- Implement evaluation scripts that consume ranked retrieval results from Quân and Thiện and output per-query scores plus aggregate tables.
- Verify source-location matching for PDF pages and audio/video time spans.
- Produce reproducible tables by retrieval configuration, source/query category, and single- versus cross-source questions.
- Keep answer correctness/faithfulness separate from retrieval ranking and evidence coverage.
- Store only synthetic or consented content. Keep personal data out of benchmark files and presentation screenshots unless specifically approved.

## Four-week checkpoints

### Week 1 — Protocol and annotation rules

- Deliver metric definitions and a draft annotation guide.
- Agree with Hao on question categories, with Tài on paired transcript cases, and with Quân/Thiện on result formats.

### Week 2 — Pilot dataset and scorer

- Label a small starter set and test the annotation rules with a teammate.
- Implement the result ingestion and at least one metric end-to-end.
- Validate evidence group handling with cross-source examples.

### Week 3 — Full pilot scoring

- Complete the 20–30 question pilot if source material and time allow; otherwise report actual count and gaps.
- Score the same queries across the primary retrieval conditions.
- Review disagreements and inspect false positives, misses, and incomplete cross-source evidence.

### Week 4 — Findings and evaluation story

- Produce tables and concise plots or examples for the presentation.
- State sample size, annotation limits, held-out status, and uncertainty plainly.
- Report answer faithfulness only as a secondary analysis with its own human-review evidence.

## Deliverables and acceptance checklist

- [ ] Annotation guide with relevant evidence, alternatives, evidence groups, answerability, and source locations.
- [ ] Versioned pilot question/evidence dataset with privacy-safe content.
- [ ] Reproducible scorer and output format for each retrieval run.
- [ ] Cross-source Complete Evidence@10 and conventional ranking metrics where labels support them.
- [ ] Per-category result tables and clear sample-size/uncertainty caveats.
- [ ] Human review procedure and logged adjudication for a sample of annotations.
- [ ] Secondary faithfulness protocol kept distinct from primary retrieval evaluation.

## Handoffs and presentation segment

Give Hao metric definitions and clean result tables; give Quân/Thiện sample labels and expected result schema; provide Tài paired clean/ASR questions and evidence locations; ask all members to annotate or review a small shared sample. Your presentation section explains what “success” means, how cross-source completeness is scored, and what the pilot can and cannot establish.

## Risks to watch

- Letting the person who built a method silently label all of its own outputs without a review rule.
- Marking only one passage as relevant when multiple evidence groups are required.
- Reporting one aggregate number that hides weak audio/video or cross-source performance.
- Treating an unanswerable question as a retrieval miss without a defined policy.
- Calling a tiny pilot statistically conclusive or using answer quality to conceal retrieval limitations.
