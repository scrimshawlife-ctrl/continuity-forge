# M0 Supported Screenplay Grammar

This document defines the constructs covered by the executable M0 golden corpus.

## Supported and gated

- `INT.`, `EXT.`, `INT/EXT.`, and `I/E.` scene headings
- action paragraphs
- uppercase character cues followed by a dialogue block
- dialogue blocks containing parentheticals and multiple nonblank lines
- uppercase dialogue text after a character cue
- Fountain transitions `CUT TO:`, `FADE IN:`, and `FADE OUT.` when they occur after a scene heading
- Fountain title-page metadata entries in `Key: Value` form
- indented continuation lines attached to the preceding metadata entry
- multiple scenes
- UTF-8 screenplay text and byte-accurate source accounting
- Final Draft XML (`.fdx`) normalization for scene heading, action, character, dialogue, parenthetical, and transition paragraph types

Supported fixtures must satisfy all of the following:

- deterministic `CompileResult` serialization
- stable script, scene, and atom identifiers
- at least one emitted scene
- zero uncovered non-whitespace source bytes
- no `CF_COVERAGE_UNEMITTED_SOURCE` diagnostic
- no error-severity diagnostic
- valid ordered source spans for every atom and metadata entry

## Title-page metadata semantics

Before the first scene heading, a nonblank line matching `Key: Value` opens a `ScriptMetadataEntry` with a normalized lowercase key, preserved value, and exact source span.

Subsequent indented nonblank lines extend that entry. Continuation text is newline-joined in source order, and the entry source span expands through the final continuation line. A blank line closes the active metadata entry.

Metadata remains separate from narrative atoms and does not receive a synthetic scene ID. Its source spans participate in coverage accounting, so valid title-page blocks do not create silent omissions.

Unindented pre-scene text that does not match `Key: Value` remains diagnostic input.

## Dialogue-block semantics

A character cue opens a dialogue block. Every following nonblank line—including parentheticals—is accumulated into one `DIALOGUE` atom until a blank line or end of file. The atom source span begins at the character cue and ends at the last dialogue line.

This preserves the performance unit as one provenance-bearing atom without requiring a separate parenthetical atom type during M0.

## Parser precedence

M0 classifies nonblank screenplay lines in this order:

1. active dialogue-block content
2. scene heading
3. indented continuation of active pre-scene metadata
4. new pre-scene `Key: Value` metadata
5. transition
6. new character cue
7. action

This ordering prevents uppercase dialogue, parentheticals, transitions, and title-page metadata from being misclassified.

## Detected but not accepted as clean input

- non-metadata content before the first scene heading, including an opening `FADE IN:`
- orphan character cues
- screenplay text containing no scene headings
- malformed FDX XML
- unsupported file suffixes or API source formats

These inputs fail closed or produce typed diagnostics. They are not part of the zero-omission corpus.

## Deferred grammar

- dual dialogue
- centered text
- lyrics
- notes, boneyards, sections, and synopses
- forced Fountain elements
- page breaks
- revision marks

Deferred constructs must not be described as supported until fixtures and deterministic parser tests exist.
