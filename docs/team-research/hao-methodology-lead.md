# Hao — Research Methodology and Integration Lead

**Team role:** Leader and Member 1 in the research proposal  
**Primary ownership:** Keep the question, hypotheses, system interfaces, experiment design, and final presentation aligned.

## Mission

Lead the team to a reproducible four-week research demonstration of unified retrieval across messages, PDFs, audio transcripts, and video transcripts. Coordinate the components and make sure the team presents what it measured, not what it hopes to prove.

## Questions you should be able to answer

1. What exactly does “unified retrieval” mean in this study, and what is the boundary of the prototype?
2. What is the closest prior work, and which claims of novelty can we responsibly make after reviewing it?
3. Are H1–H4 measurable with the planned dataset and metrics? What outcome would count against each hypothesis?
4. Which variables must remain fixed so the BM25, dense, and reranked comparisons are fair?
5. How will the system preserve source identity and location from ingestion through retrieved evidence and answer citations?
6. What minimum results would support the presentation, and what limitations must be stated?

## Research and coordination tasks

- Consolidate literature notes from all members and verify the closest related studies, datasets, and benchmark conventions.
- Finalize operational definitions for source type, relevant passage, required evidence, cross-source completeness, latency, and faithfulness.
- Approve the common experiment matrix: BM25; BGE-M3 dense; BGE-M3 dense with BGE reranker; optional BM25+dense hybrid only if time permits.
- Set fixed corpus splits, chunking rules, query set, top-k values, reranking candidate count, hardware/runtime logging, and random seeds where applicable.
- Define shared component interfaces: normalized source record, chunk and source-location schema, retrieval result, and evaluator input.
- Run short weekly check-ins. Track blockers, decisions, owners, and handoff dates; invite a teammate to review each member's output.
- Integrate the architecture, method, results, limitations, and demo into one presentation narrative.

## Four-week checkpoints

### Week 1 — Scope and method

- Publish the one-page research question, hypotheses, related-work boundary, and experiment matrix.
- Agree on canonical source/chunk metadata and evaluation terms with Thiện, Quân, Tai, and Xuân Ngân.
- Record which model choices are provisional and what evidence is needed before locking them.

### Week 2 — Component interfaces

- Review each team's minimum component demo and configuration note.
- Resolve integration questions before the individual implementations diverge.
- Confirm the query, chunk, source ID, and location fields flow end-to-end.

### Week 3 — Integration and pilot

- Coordinate one small end-to-end corpus across all four source types.
- Ask Xuân Ngân to validate pilot labels and Tai/Quân to compare initial runs under identical conditions.
- Document bugs, protocol changes, and why any changes are necessary; do not silently change the benchmark mid-comparison.

### Week 4 — Reproducible presentation

- Freeze the pilot protocol and label which results are preliminary.
- Assemble architecture, method, results, error analysis, limitations, and demonstration.
- Check that every chart has its corpus split, query count, model/configuration, and metric definition.

## Deliverables and acceptance checklist

- [ ] Final research question, scoped claims, and verified related-work summary.
- [ ] Architecture and data-flow view with interfaces and source-location handling.
- [ ] Experiment matrix with controlled variables, metrics, and run settings.
- [ ] Integrated prototype plan and working end-to-end demo supported by other owners.
- [ ] Presentation narrative, division of speaking parts, and proposed contributions.
- [ ] Reproducibility and limitation checklist; no claim exceeds the observed pilot evidence.

## Handoffs and presentation segment

Request model assumptions and runtime settings from Thiện and Quân; retrieval configuration and latency breakdown from Tai; dataset definition, label rules, and metric results from Xuân Ngân. Your presentation section frames the problem, explains the controlled methodology, connects each component to the research question, and closes with limitations and the next experiment.

## Risks to watch

- Expanding the project into a complete messaging product before answering the retrieval question.
- Changing models, chunking, or test queries between configurations and presenting the comparison as controlled.
- Overstating novelty or treating the hypotheses as expected outcomes.
- Losing PDF page or media timestamp provenance during chunking.
- Letting answer quality obscure retrieval failures; report the primary retrieval metrics independently.
