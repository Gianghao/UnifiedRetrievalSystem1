# Project vision

## Purpose

Build a private messaging workspace where people can later ask questions about what was shared in a conversation. The planned assistant should retrieve relevant messages and attachment evidence, show where each answer came from, and say when the conversation does not support an answer.

The assistant is a planned capability, not a feature of the current app. The current milestone establishes messaging, attachments, and a browsable conversation archive that later processing can build on.

## Expected product outcome

A user can sign in, exchange durable messages and supported attachments with an explicitly connected contact, return to a conversation, browse its shared media/files/links, and search or ask questions over authorized conversation evidence. Answers should cite message or media locations so users can inspect the source themselves. Ordinary messaging must continue to work when processing or retrieval services are unavailable.

The finished system should support controlled retrieval experiments that compare keyword, dense, hybrid, and reranked retrieval against a versioned evaluation corpus. It should record dataset and model versions, configuration, latency, and retrieval metrics so improvements can be reproduced rather than assumed.

## Product principles

- Conversation membership determines access to every message, attachment, extracted artifact, search result, and answer.
- PostgreSQL remains the source of truth for durable messages and metadata. Realtime events notify clients to reload state.
- Derived evidence links back to its source message, attachment, page, or timestamp.
- Attachments, transcripts, chunks, embeddings, previews, caches, logs, and backups need an explicit retention and deletion policy.
- Retrieved conversation content is untrusted input. It cannot change system instructions or grant access to another conversation.
- Use local inference by default for private content. Any external provider needs explicit configuration and a clear data policy.
- State clearly that server-side AI processing is not end-to-end encryption.

## Scope

Planned source types include text messages, PDFs, audio, and video audio tracks. Images and links may be searchable through metadata, OCR, or page extraction only after those processing paths have been explicitly designed and tested. Video-frame understanding is a separate scope decision.

The intended retrieval pipeline is: secure upload and validation; asynchronous extraction; canonical source-linked chunks; authorized keyword and dense retrieval; optional reranking and hybrid fusion; answer generation grounded only in returned evidence; and independent evaluation.

## Measures of readiness

- Message and attachment operations enforce authorization and survive retries/reconnects.
- Retention tests prove that expired source and derived data are inaccessible and cleaned up according to policy.
- Retrieval uses stable source locations and identical corpus splits across methods.
- Evaluation reports Recall@10, nDCG@10, MRR, candidate recall, latency, and source attribution accuracy. Audio transcription is evaluated separately with word error rate.
- Answer quality is not used to hide weak retrieval. Each answer can be traced to evidence and fails closed when evidence is insufficient.
- Setup, migration, restore, and local evaluation steps are reproducible by another contributor.

## Out of scope for the current increment

Production deployment, real SMS delivery, end-to-end encrypted messaging, regulated data handling, large-scale multi-tenant operation, and AI retrieval or inference are not implemented. They need separate designs and verification before use with sensitive data.
