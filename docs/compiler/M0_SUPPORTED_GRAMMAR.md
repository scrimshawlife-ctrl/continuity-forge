# M0 Supported Screenplay Grammar

This document defines the constructs covered by the executable M0 golden corpus.

## Supported and gated

- `INT.`, `EXT.`, `INT/EXT.`, and `I/E.` scene headings
- action paragraphs
- uppercase character cues followed by a dialogue block
- dialogue blocks containing parentheticals and multiple nonblank lines
- uppercase dialogue text after a character cue
- Fountain transitions `CUT TO:`, `FADE IN:`, and `FADE OUT.` when they occur after a scene heading
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
- valid ordered source spans for every atom

## Dialogue-block semantics

A character cue opens a dialogue block. Every following nonblank line—including parentheticals—is accumulated into one `DIALOGUE` atom until a blank line or end of file. The atom source span begins at the character cue and ends at the last dialogue line.

This preserves the performance unit as one provenance-bearing atom without requiring a separate parenthetical atom type during M0.

## Parser precedence

M0 classifies nonblank screenplay lines in this order:

1. active dialogue-block content
2. scene heading
3. transition
4. new character cue
5. action

This ordering prevents uppercase dialogue, parentheticals, and transition tokens from being misclassified as character cues.

## Detected but not accepted as clean input

- content before the first scene heading, including an opening `FADE IN:`
- orphan character cues
- screenplay text containing no scene headings
- malformed FDX XML
- unsupported file suffixes or API source formats

These inputs fail closed or produce typed diagnostics. They are not part of the zero-omission corpus.

## Deferred grammar

- dual dialogue
- centered text
- lyrics
- notes, boneyards, sections, synopses, and title pages
- forced Fountain elements
- page breaks
- revision marks

Deferred constructs must not be described as supported until fixtures and deterministic parser tests exist.
