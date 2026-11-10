# Tài — Speech Recognition and Media Processing Researcher

**Team role:** Member 2 in the research proposal  
**Primary ownership:** Make audio and video speech searchable while measuring how recognition errors affect retrieval.

## Mission

Produce source-linked searchable text from audio and video, and design a small controlled comparison that shows whether recognition errors change retrieval effectiveness. Also support PDF extraction so every modality enters the unified text pipeline with reliable source locations.

## Questions to investigate

1. How does Whisper large-v3 perform on our selected recordings, and what is its measured Word Error Rate (WER)?
2. Which errors matter most for search: names, numbers, technical terms, negation, or changed relationships between words?
3. Does retrieval quality decline from human-corrected transcripts to ASR transcripts on the same recordings and questions?
4. Are the error patterns different across language, recording quality, speakers, or source type?
5. How should transcript segments preserve timestamps so a retrieved answer can be checked against the original media?
6. What does PDF extraction preserve or lose, and how can page locations remain attached to chunks?

## Research tasks

- Read and summarize Whisper's architecture, inference process, supported languages, timestamp behavior, resource needs, and limitations using reliable primary documentation/research.
- Compare one plausible alternative ASR model only if the four-week scope allows; explain why Whisper remains the primary controlled baseline or revise that choice with evidence.
- Define the clean-versus-ASR paired condition. Keep the underlying recording, segmentation, question, and retrieval configuration constant.
- Establish a transcript review protocol that records substitutions, deletions, insertions, names, numerals, technical words, and timestamps.
- Compute WER with a documented normalization rule (for example, casing and punctuation treatment). Report dataset size and language.
- Extract PDF text with page numbers and record extraction failures or scanned-PDF limitations.

## Technical work

- Build a repeatable audio/video processing script or service that extracts audio as needed and emits timestamped transcript segments.
- Keep original file/source IDs and media time ranges in a canonical record; do not flatten the transcript into location-free text.
- Produce paired corrected and ASR transcript records from the same source where consent and time permit.
- Make transcript output compatible with shared chunking/indexing interfaces agreed with Hao and Quân.
- For the pilot, use a small representative set and document hardware, model revision, inference options, language settings, and runtime.

## Four-week checkpoints

### Week 1 — Method and sample

- Write a concise ASR model note and identify data, consent, language, and hardware constraints.
- Agree on transcript schema, timestamp precision, PDF page metadata, and clean-transcript annotation procedure.

### Week 2 — Minimum working processing

- Demonstrate one audio transcription and one video audio extraction/transcription with inspectable timestamps.
- Demonstrate PDF extraction with page-numbered text, noting scanned documents that need OCR.
- Record exact model and processing settings.

### Week 3 — Paired transcript pilot

- Prepare clean and ASR variants for the same recordings where possible.
- Compute WER and run retrieval comparisons using identical queries and chunking, coordinating with Quân, Thiện, and Xuân Ngân.
- Review examples where ASR changes the retrievability of important evidence.

### Week 4 — Results and demonstration

- Present a media-processing demonstration and a small WER/error analysis.
- Report retrieval metrics separately for clean and ASR transcript conditions, with sample size and limitations.
- Explain timestamp provenance and known processing failures.

## Deliverables and acceptance checklist

- [ ] Evidence-backed ASR model justification and limitation note.
- [ ] Repeatable audio/video transcription path with source IDs and timestamped segments.
- [ ] Repeatable PDF text extraction output with page references or clear failure reporting.
- [ ] Paired clean-versus-ASR sample and documented WER procedure/results.
- [ ] Examples connecting specific ASR errors to retrieval successes or misses.
- [ ] Configuration record sufficient for another teammate to reproduce the pilot.

## Handoffs and presentation segment

Provide Quân and Thiện searchable segment text plus source/time metadata; give Xuân Ngân both corrected and ASR variants with alignment notes; give Hao model settings, WER method, failures, and runtime. Your presentation section explains how media becomes evidence and what the pilot says about ASR-error propagation—without claiming general performance from a small sample.

## Risks to watch

- Comparing transcripts from different recordings or with different queries and attributing the result to ASR error.
- Reporting WER without explaining normalization or language.
- Losing time offsets or PDF page numbers during preprocessing.
- Treating automatic transcripts as verified ground truth.
- Using private recordings without permission or moving sensitive media into an unapproved shared dataset.
