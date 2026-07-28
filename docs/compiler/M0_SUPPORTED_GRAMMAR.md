# M0 Supported Screenplay Grammar

This document defines the constructs covered by the executable M0 golden corpus.

## Supported and gated

- `INT.`, `EXT.`, `INT/EXT.`, and `I/E.` scene headings
- action paragraphs
- uppercase character cues followed by one dialogue paragraph
- multiple scenes
- UTF-8 screenplay text and byte-accurate source accounting
- Final Draft XML (`.fdx`) normalization for scene heading, action, character, dialogue, and transition paragraph types

Supported fixtures must satisfy all of the following:

- deterministic `CompileResult` serialization
- stable script, scene, and atom identifiers
- at least one emitted scene
- zero uncovered non-whitespace source bytes
- no `CF_COVERAGE_UNEMITTED_SOURCE` diagnostic
- no error-severity diagnostic
- valid ordered source spans for every atom

## Detected but not accepted as clean input

- content before the first scene heading
- orphan character cues
- screenplay text containing no scene headings
- malformed FDX XML
- unsupported file suffixes or API source formats

These inputs fail closed or produce typed diagnostics. They are not part of the zero-omission corpus.

## Deferred grammar

- transitions in Fountain source, including `CUT TO:`, `FADE IN:`, and `FADE OUT.`
- parentheticals and dialogue continuations
- dual dialogue
- centered text
- lyrics
- notes, boneyards, sections, synopses, and title pages
- forced Fountain elements
- page breaks
- revision marks

Deferred constructs must not be described as supported until fixtures and deterministic parser tests exist. FDX transition paragraphs may normalize into text, but clean Fountain transition classification is not yet an M0 acceptance gate.
