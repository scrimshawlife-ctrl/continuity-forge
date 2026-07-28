# M0 Supported Screenplay Grammar

This document defines the constructs covered by the executable M0 golden corpus
and the deterministic compiler spine.

## Supported and gated

### Fountain

- Scene headings: `INT.`, `EXT.`, `EST.`, `INT/EXT.`, `INT./EXT.`, `I/E.`, and forced `.heading`
- Action paragraphs, including forced action (`!…`)
- Character cues (uppercase and `@Name`), including parenthetical extensions such as `(V.O.)`
- Parenthetical lines as distinct `parenthetical` atoms inside a dialogue block
- Multi-line dialogue after a character cue until a blank line or structural break
- Dual-dialogue marker (`^`) stripped from the cue text
- Transitions: known constants and uppercase `… TO:` / forced `>…`
- Title-page `Key: Value` lines before the first blank/non-title content
- Sections (`#`), synopses (`=`), notes (`[[…]]`), centered (`>…<`), lyrics (`~`), page breaks (`===`)
- Boneyards (`/* … */`), including live text after a terminator on the same line
- Multiple scenes, including repeated sluglines with distinct occurrence IDs
- UTF-8 source text with contiguous byte-accurate source segments

### Final Draft XML (`.fdx`)

- Paragraph types: Scene Heading, Action, Character, Parenthetical, Dialogue, Transition
- Unsupported paragraph types retained as action with `FDX101` warning
- Malformed XML fails closed with `FDX100` / `FDX102` diagnostics and full source accounting

### Identity and provenance

- Optional `document_key` pins logical script identity across revisions
- When `document_key` is omitted, identity is derived from the source hash
- Optional `prior=` Production IR reconciles scene/atom IDs for duplicate-heavy revisions
- Every atom carries a source span; source segments partition the full input
- Coverage ratio must be `1.0` with zero uncovered spans for corpus fixtures

## Golden corpus fixtures

| Fixture | Intent |
|---------|--------|
| `minimal.fountain` / `minimal.fdx` | Bootstrap happy path |
| `advanced.fountain` / `advanced.fdx` | Controls, notes, multi-scene FDX |
| `continuity.fountain` | Props, wardrobe, injury, entrances/exits, setup/payoff |
| `dialogue_heavy.fountain` | V.O., parentheticals, `@` cues, dual dialogue |
| `flashback.fountain` | Flashback/present headings and transitions |
| `ambiguous.fountain` | Long uppercase action, forced elements, inline boneyard |
| `duplicate_scenes.fountain` | Repeated sluglines with distinct IDs |
| `unicode.fountain` | Non-ASCII dialogue and action provenance |
| `malformed.fountain` / `malformed.fdx` | Fail-closed diagnostics with full accounting |

## Detected but not clean

- Non-title content before the first scene heading (`CF101` warning, retained in preamble)
- Unclosed boneyard (`CF102` error)
- No scene headings (`CF100` / `FDX102` error)
- Malformed FDX XML (`FDX100` error)

These inputs remain fully source-accounted; they are not silent omissions.

## Deferred beyond M0 atomizer

Typed continuity entities (props, wardrobe, injury bands, setup/payoff links),
Temporal workflows, provider execution, mutating MCP tools, and autonomous
rewriting belong to later milestones. M0 preserves their screenplay text as
provenance-bearing atoms without claiming semantic ledger extraction.
