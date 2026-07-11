# Annotation standard

The product goal is comprehension, not automatic paraphrase. Every annotation
must be linked to a stable source anchor and contain the following fields.

All reader-facing fields in v0.1 must be written in Simplified Chinese. The
source text and its stable anchor remain unchanged.

| Field | Required behaviour |
| --- | --- |
| anchor | Must exactly match a source paragraph anchor such as P014. |
| role | Explain what the passage does in the paper: defines, motivates, specifies a method, reports evidence, qualifies a claim, and so on. |
| context | Explain how the passage connects to nearby text and the paper-level argument. |
| explanation | Explain the substantive idea, term, assumption, formula purpose, or result without merely restating the source. |
| takeaway | State the point a reader should retain. |
| caveat | State a source-grounded ambiguity, boundary, or explicitly say that no additional caveat is needed. |
| translation | A faithful Chinese translation only when full-translation mode is selected; otherwise an empty field. |

## Non-negotiable checks

1. Every extracted paragraph must receive exactly one annotation.
2. No annotation may target an anchor that does not exist in the source.
3. The renderer must show the same anchor in the source and note columns.
4. Notes must distinguish author claims from the reader-facing explanation.
5. Unsupported interpretation must be placed in caveat or omitted.

## What good looks like

Weak note:

> This paragraph introduces the model.

Useful note:

> This passage turns the paper's broad problem into an operational model. It
> follows the motivation section and establishes the variables used in the
> results that follow. The reader should identify which assumptions make the
> later conclusion applicable; those assumptions are limits on the claim, not
> merely technical notation.

## Quality boundary for v0.1

The tool checks correspondence and required fields automatically. It cannot
prove that a model's academic interpretation is correct. Readers should inspect
the original source and treat notes as reading support, not as a replacement for
the paper.
