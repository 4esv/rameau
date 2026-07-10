# Music dataset — init brief

> Name: TBD — unnamed for now, to be chosen later.

> Seed brief. This is the input a planning agent consumes to produce `plan.md`.
> It captures decisions already made and the open questions still to resolve.
> It is **not** an implementation plan.

## The goal

A **text→text** dataset (and, downstream, an eval and optionally a small model)
that teaches functional-harmony understanding in **music notation**. Useful two
ways: to a musician directly, and as training/eval fuel for a model assisting a
musician. Text→text is a deliberate choice — it's the shape musicians and
tool-calling assistants actually use, and it sidesteps the GPU bill of audio.

## The core insight (why this is buildable cheaply)

You do **not** hand-label harmony. Ground truth is generatable:

1. **Deterministic analysis** — `music21` (MIT) parses scores and produces
   Roman-numeral / functional analysis programmatically. Feed it real
   progressions, get gold labels for free, no GPU.
2. **Human-annotated corpora already exist** — see sources below. These give a
   gold layer that a deterministic tool can't (voice-leading, expert reharm
   choices, disputed analyses).

The dataset is the contribution and the moat. A model is a follow-on, not the
point.

## v1 task (start here — one transform, one representation)

**Functional analysis of a chord progression.**

```
in:  key: C major
     progression: Dm7 G7 Cmaj7
out: ii7 – V7 – Imaj7   ·   perfect authentic cadence
```

Chosen because: gold is deterministic and verifiable, it's squarely in the
harmony wheelhouse (chordvery / pianito), and it's immediately useful both to a
musician and as a tool an assistant-LLM can call. v2 candidates once the vocab
pipeline exists: reharmonization, 4-bar continuation, representation-translation
(chord symbols ↔ Roman numerals ↔ voicings ↔ ABC).

## Decisions to make (flag in plan.md)

- **Representation.** Chord symbols vs ABC (melody) vs Humdrum `**kern` vs
  MusicXML. Lean chord-symbol + Roman-numeral for v1 (harmony-first). ABC is the
  better choice if the project pivots to melody/continuation.
- **Roman-numeral convention.** Which standard (DCML harmony syntax, `rntxt`,
  music21's) — pick one and normalize everything to it. Inconsistency here is
  the whole game.
- **Split design.** Train/val/**test** with no leakage across pieces or
  composers. Because gold is deterministic, the test set doubles as a benchmark.

## The sneaky-high-value angle: publish an eval, not just data

Because the gold is deterministic and verifiable, you get a **benchmark for
free**: how badly do frontier models mangle Roman numerals / ABC / `**kern`?
A music-notation-reasoning eval is paper-shaped, gets attention, and costs less
than training anything. Strongly consider shipping the eval split as a first-class
artifact alongside the dataset.

## Optional model path (later, local, cheap)

You already run ollama/qwen locally (see the pi offline-agent setup). A LoRA on
**Qwen2.5-0.5B/1.5B** or a **flan-T5-small** fine-tune trains on MPS with no cloud
bill. This is a follow-on to the dataset, not a blocker.

## Data sources (planner: verify repos + licenses)

- **music21** — https://web.mit.edu/music21/ — parsing, corpus, Roman-numeral
  analysis. Primary ground-truth generator.
- **DCML corpora** — github.com/DCMLab — Annotated Beethoven Corpus (string
  quartets), Mozart piano sonatas, romantic piano corpus, etc. Harmony labels in
  TSV using the DCML annotation standard. **Check licenses — often CC-BY-NC-SA;
  scores are PD but annotations are separately licensed.**
- **When-in-Rome** (Mark Gotham) — github.com/MarkGotham/When-in-Rome —
  aggregated Roman-numeral analyses (`rntxt`).
- **ABC / melody** (if the project pivots): thesession.org data dump, the
  Nottingham dataset.
- **HF datasets docs** — for dataset-card structure, splits, `datasets` loading.

## Deliverable shape on HF

- A dataset repo with a proper **dataset card** (provenance, license,
  generation method, known limitations), clean train/val/test splits, and a
  `datasets`-loadable format.
- Attribution + license hygiene is load-bearing — this is the difference between
  "curated contribution" and "scraped pile." Get it right; it's the whole
  credibility of the artifact.

## Suggested milestones (planner refines into `plan.md`)

- **Phase 0 — seed** (this doc, dir). ✅
- **Phase 1 — pipeline.** music21 → `(key + progression → Roman-numeral analysis
  + cadence)` pairs from one corpus. Prove the labels are right on a hand-checked
  sample.
- **Phase 2 — scale + clean.** Add corpora, normalize to one Roman-numeral
  convention, dedupe, leakage-free splits.
- **Phase 3 — publish.** Dataset card, license/attribution, push to HF.
- **Phase 4 (optional) — eval + model.** Benchmark frontier models on the test
  split; LoRA a small local model.

## Non-goals

- Not audio generation. Text/notation only.
- Not a from-scratch music-theory engine — stand on music21 / existing corpora.
- Not a giant model. The dataset (and eval) is the deliverable.

## Note to the planning agent

Per Axel's convention, produce a `plan.md` (path is unknown and branching).
Resolve the representation + Roman-numeral-convention decisions or surface them
to Axel first — they're upstream of everything. Verify corpus licenses **before**
building on any source; a license problem found at Phase 3 wastes Phases 1–2.
