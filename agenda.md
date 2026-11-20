# Week 1 Research Meeting

## Progress review agenda and recurring PM checklist

> A 90-minute Week 1 meeting plan for reviewing each workstream, aligning the research method, and assigning dated Week 2 deliverables.

- **Meeting type:** Week 1 progress review and methodology alignment
- **Facilitator:** Hao, project manager
- **Suggested length:** 90 minutes
- **Purpose:** Hear a concise evidence-based update from each workstream, settle the decisions that affect Week 2 prototypes, and leave with named owners and dates for every next deliverable.

# Meeting outcome

At the end of this meeting, the team should have:

- A shared, one-sentence research question and agreed scope: retrieval across text messages, PDFs, audio transcripts, and video transcripts.
- A hypothesis and experiment matrix that treats all proposed outcomes as open questions.
- Provisional model/method choices and the evidence still needed to confirm them.
- Agreed source, chunk, and retrieval-result fields so the components can connect in Week 3.
- A draft evaluation and annotation protocol, including cross-source evidence groups.
- A Week 2 task list with one owner, a concrete acceptance check, and a due date for each task.
- A written record of risks, unresolved questions, and decisions.

# Ask each member to prepare

Bring a five-minute update and one concise artifact: a short literature/model note, a diagram, a prototype, a sample annotation, or a measured example. Do not use an unsupported accuracy claim as a result. For each finding, identify the source or evidence and state what remains uncertain.

Use the same report format:

1. **Commitment:** What did you agree to complete this week?
2. **Evidence:** What artifact, source, example, or measurement shows the work done?
3. **Finding:** What did you learn, and which project question does it answer?
4. **Risk or blocker:** What might stop the next milestone, and what help or decision is needed?
5. **Next deliverable:** What will you hand off, to whom, by what date, and how will the team verify it?

If a task is unfinished, report the remaining work and revised estimate. Do not report only a percentage complete.

# Proposed 90-minute agenda

| Time | Topic | Lead | Required output |
| :---- | :---- | :---- | :---- |
| 0–5 min | Open, confirm purpose, review previous commitments if applicable | Hao | Meeting target and timebox confirmed |
| 5–10 min | Restate the research question, four source types, four-week deadline, and primary/secondary scope | Hao | Any scope disagreement recorded |
| 10–50 min | Five member reports: 6 minutes each, followed by 2 minutes of clarifying questions | All, Hao keeps time | Status, evidence, blocker, next deliverable captured for each owner |
| 50–65 min | Align architecture and interfaces: ingestion metadata, chunk fields, retrieval output, evaluator input | Hao with Thiện, Quân, Tai, Xuân Ngân | Draft shared data contract and named owner for unresolved fields |
| 65–75 min | Review experiment matrix and controls | Hao with Quân and Thiện| BM25, dense, reranked conditions; optional hybrid scope decision |
| 75–83 min | Review dataset, annotation rules, consent, and metrics | Xuân Ngân with Tài| Pilot data plan and draft evidence-label protocol |
| 83–88 min | Assign Week 2 deliverables, dates, acceptance checks, and dependency order | Hao | Action log complete; blockers have mitigation owners |
| 88–90 min | Read back decisions and due dates; confirm next check-in | Hao | Each owner confirms their next commitment |

If discussion runs long, put unresolved topics in the decision log with an owner and resolution date. Do not let an open debate consume the assignment and deadline review at the end.

# Round-robin report prompts

## Hao — research methodology and integration

- Is the question precise enough to test: retrieval effectiveness across source types and retrieval strategies, including latency and answer faithfulness?
- What related work and novelty boundaries still need verification?
- Are H1–H4 measurable with the proposed pilot and metrics? What result would contradict each hypothesis?
- Which experiment conditions and variables must remain fixed?
- What decisions does the team need today to start Week 2 work?

**Week 1 evidence to bring:** draft research framing, hypothesis-to-metric mapping, experiment matrix, and a first-pass architecture/interface view.

## Tài — speech recognition and media processing

- What did you learn about Whisper large-v3, its multilingual behavior, timestamp outputs, hardware needs, and limitations?
- Which audio/video sample can support a paired clean-versus-ASR comparison?
- How will you normalize transcripts and calculate WER?
- How will transcript segments preserve source IDs and start/end times? How will PDF extraction preserve page numbers?
- What consent, language, recording-quality, or processing constraint is the main risk?

**Week 1 evidence to bring:** model note, candidate data and processing plan, draft transcript/PDF metadata, and a WER protocol. A functioning full pipeline is a Week 2 target, not a Week 1 requirement.

## Quân — dense retrieval and embeddings

- What evidence supports BGE-M3 as the dense-retrieval baseline, and which alternative is worth a bounded comparison?
- How should chunks, vector dimensions, normalization, similarity, and model version be controlled?
- How will dense results retain message/file IDs and page or timestamp locations?
- Which sample queries can reveal paraphrase, exact-term, and cross-source behavior?
- What memory, index-time, or query-latency limitation might constrain the pilot?

**Week 1 evidence to bring:** model comparison note, proposed chunk/vector settings, a draft result contract, and a small set of diagnostic queries.

## Thiện — BM25, retrieval strategies, and reranking

- What should the BM25 baseline tokenize or normalize, and where should it be strong?
  - It is strong for searching something like a serial code, an id because those may not be in the training set of an embedding search, then it may skip them.
- What supports using BGE-reranker-v2-m3, and what is its runtime cost?
- Can the proposed dense top-50 then rerank-to-top-10 fit the available hardware and time?
- How will candidate recall, reranking latency, and end-to-end latency be reported separately?
- Should hybrid retrieval remain optional until the three primary conditions are working?

**Week 1 evidence to bring:** concise BM25/reranker notes, candidate and final top-k proposal, latency measurement plan, and interface dependencies.

## Xuân Ngân — benchmark, annotation, and evaluation

- What precisely counts as relevant evidence, an acceptable alternative, and a complete answer for cross-source questions?
- How will answerable and unanswerable questions be represented?
- Which metrics can be computed reliably from the labels and returned rankings?
- How will labels receive a second-person review and disagreements get resolved?
- What synthetic or consented materials can form a 20–30 question pilot, and what will that small sample not support claiming?

**Week 1 evidence to bring:** draft metric definitions, annotation template, example single-source and cross-source labels, and a pilot corpus plan.

# Week 1 exit checks

Before closing, Hao should be able to check each item as complete or record an owner and due date:

- [ ] Every member has shared a concrete artifact or evidence-backed research note.
- [ ] The scope and primary research question are agreed by all five members.
- [ ] H1–H4 have a metric or analysis plan, plus a stated possible disconfirming outcome.
- [ ] BM25, BGE-M3 dense, and dense-plus-reranker are identified as primary proposed comparisons; hybrid is explicitly optional.
- [ ] The team has a draft common chunk/result schema with source IDs and locations.
- [ ] The pilot data plan covers all four source categories and records consent/privacy constraints.
- [ ] Xuân Ngân has a draft annotation and scoring protocol, including cross-source evidence groups.
- [ ] Week 2 component demonstrations each have an owner, due date, dependencies, and acceptance check.
- [ ] Decisions, risks, unresolved questions, and next meeting date are written down.

# PM checklist for every meeting

Use this before, during, and immediately after each team meeting. Keep one shared action log and decision log so commitments do not disappear into chat history.

## Before the meeting

- [ ] Check the four-week milestone calendar and list deliverables due before the next meeting.
- [ ] Review the prior action log. Mark items complete only when the promised artifact or evidence is available.
- [ ] Ask each owner to submit status, evidence link, blocker, next step, estimate, and any decision needed.
- [ ] Identify dependencies between ingestion, chunking/embeddings, retrieval, and evaluation; invite the owners needed to resolve them.
- [ ] Set an agenda with time for each owner and protect time at the end to assign dated actions.
- [ ] Flag any task that cannot be completed by its due date early enough to change scope, add help, or reorder work.

## During the meeting

- [ ] Hear from every owner, including work that is behind schedule. Ask for a visible artifact or concrete evidence.
- [ ] For each task, record the owner, deliverable, acceptance check, due date, status, dependency, and next action.
- [ ] Ask what changed since the previous update and what could make the current estimate wrong.
- [ ] Check that blockers have a person responsible for removing them and a date for the follow-up.
- [ ] Separate a finding from a hypothesis, assumption, or interpretation. Ask what evidence supports a claim.
- [ ] Check experimental fairness: same corpus, queries, chunking, labels, retrieval cutoff, and evaluation protocol across configurations unless a change is explicitly part of the experiment.
- [ ] Check that source type is not provided to retrieval as a hidden hint in the unified-index experiment.
- [ ] Keep retrieval results, answer generation, WER, and answer faithfulness as distinct measurements.
- [ ] Record decisions with rationale, affected tasks, decision owner, and any revisit condition.
- [ ] Park topics that do not affect the current milestone, assigning an owner and date if they need later research.
- [ ] Reserve the last minutes to read action items aloud; each owner confirms their commitment.

## After the meeting

- [ ] Send or save notes with decisions, action owners, dates, dependencies, risks, and the next meeting time.
- [ ] Update the four-week plan and action log on the same day.
- [ ] Follow up directly on critical blockers before they threaten the next milestone.
- [ ] Review promised artifacts against their acceptance checks; ask for a specific correction when an item is incomplete.
- [ ] Escalate schedule risk while there is still time to reassign work or narrow scope.
- [ ] Track unplanned scope changes so they do not silently displace required presentation deliverables.

# Status and escalation rules

Use simple statuses and record the reason:

- **On track:** The owner expects to meet the date, and current evidence supports that estimate.
- **At risk:** A named dependency, missing evidence, or likely rework threatens the date; record a mitigation owner and check-in date.
- **Blocked:** Progress requires a decision, resource, or external input; name who will resolve it and by when.
- **Done:** The artifact exists and meets its written acceptance check. “Code written” or “research read” alone is not acceptance evidence.

When a milestone turns at risk or blocked, decide whether to add help, reorder dependencies, reduce optional scope, or move the date. Record the choice and its effect on the Week 4 presentation. Do not silently omit a deliverable.

# Reusable meeting notes

**Date / week:**

**Attendees:**

**Milestone:**

**Meeting target:**

| Owner | Deliverable | Status | Evidence and acceptance check | Next action | Due date and blocker |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Hao |  |  |  |  |  |
| Thiện |  |  |  |  |  |
| Quân |  |  |  |  |  |
| Tai |  |  |  |  |  |
| Xuân Ngân |  |  |  |  |  |

**Decisions made:**

| Decision | Reason/evidence | Owner | Affected work | Revisit condition/date |
| :---- | :---- | :---- | :---- | :---- |
|  |  |  |  |  |

**Risks and blockers:**

| Risk/blocker | Schedule or quality effect | Mitigation owner | Follow-up date |
| :---- | :---- | :---- | :---- |
|  |  |  |  |

**Next meeting:**

**Week 4 presentation impact:**