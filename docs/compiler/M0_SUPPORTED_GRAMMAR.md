# M0 Supported Screenplay Grammar

This document defines the constructs covered by the executable M0 golden corpus.

## Supported and gated

- `INT.`, `EXT.`, `INT/EXT.`, and `I/E.` scene headings
- action paragraphs
- uppercase character cues followed by one dialogue paragraph
- uppercase dialogue text after a character cue
- Fountain transitions `CUT TO:`, `FADE IN:`, and `FADE OUT.` when they occur after a scene heading
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

## Parser precedence

M0 classifies nonblank screenplay lines in this order:

1. scene heading
2. dialogue when a character cue is pending
3. transition
4. new character cue
5. action

This ordering prevents uppercase dialogue and transition tokens from being misclassified as character cues.

## Detected but not accepted as clean input

- content before the first scene heading, including an opening `FADE IN:`
- orphan character cues
- screenplay text containing no scene headings
- malformed FDX XML
- unsupported file suffixes or API source formats

These inputs fail closed or produce typed diagnostics. They are not part of the zero-omission corpus.

## Deferred grammar

- parentheticals and dialogue continuations
- dual dialogue
- centered text
- lyrics
- notes, boneyards, sections, synopses, and title pages
- forced Fountain elements
- page breaks
- revision marks

Deferred constructs must not be described as supported until fixtures and deterministic parser tests exist.
