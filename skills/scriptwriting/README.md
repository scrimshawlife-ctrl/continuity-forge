# Scriptwriting Skill — Operator Guide

## Invocation
Load `creative/scriptwriting` (or `scriptwriting`) when any narrative script task appears.

The skill announces **mode** and routes automatically.

## Effective Use
1. Provide as much of the Intake brief as possible (format, premise, protagonist, stakes, constraints, approved_canon).
2. Approve or correct foundations before asking for pages.
3. For revisions: explicitly list what is locked canon.
4. Request specific artifacts ("scene contract for scene 4", "continuity audit", "production packet for approved scenes").
5. Use with `humanizer` for final voice pass.

## Key Commands / Behaviors
- "Develop this premise into a feature outline" → DEVELOP mode, full foundations first.
- "Diagnose this scene" → DIAGNOSE, evidence + rubric + gates.
- "Rewrite this scene but keep X locked" → REVISE with canon tracking.
- "Give me production handoff for these scenes" → PRODUCTION.

## Common Pitfalls (for users)
- Asking for full screenplay before foundations → skill will push back with intake.
- Vague concepts without protagonist/agency → diagnostic only.
- Expecting instant pages on weak premise → structure first.

## Files
- SKILL.md (core)
- references/ (deep craft + schemas)
- templates/ (starters)
- evals/ (rubric + regression cases)
- CHANGELOG.md

## Validation
All core schemas parse as valid JSON. Test cases have documented expected behaviors.
