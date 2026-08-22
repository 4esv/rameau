# Paper

Draft writeup of the benchmark, for arXiv (cs.CL / cs.SD, eess.AS cross-list).

## Build

No LaTeX toolchain was available when this was drafted, so `main.tex` has been
structurally validated but **never compiled**. Compile before trusting the
layout:

```sh
brew install tectonic     # or a full TeX distribution
tectonic paper/main.tex
```

## What is verified

Every number in both tables is checked against `results/scores.json` and
`results/reasoning/scores.json` by script, not by transcription. Re-run that
check after any results change — a stale table is the easiest way for this
paper to become dishonest.

## Open before submission

- [ ] Compile it. Nobody has.
- [ ] Affiliation: currently "independent" with a personal email. Confirm this
      is right rather than a Cornell affiliation.
- [ ] Bibliography entries are hand-written from the related-work section and
      are incomplete: several lack venue, volume, or page numbers, and the
      ChatMusician and AnalysisGNN author lists are truncated. Pull proper
      BibTeX from DBLP or the ACL Anthology.
- [ ] Decide whether to run the missing Qwen3 Thinking-vs-Instruct pair before
      submitting, or leave it in Limitations as an acknowledged gap.
- [ ] Consider a prompt-sensitivity run. It is the most likely reviewer
      objection: every number here is one prompt, one run, no variance.
