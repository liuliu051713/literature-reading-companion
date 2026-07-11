# Annotation standard

The product goal is comprehension, not automatic paraphrase. Every annotation
must be linked to a stable source anchor and contain the following fields.

All reader-facing fields in v0.1 must be written in Simplified Chinese. The
source text and its stable anchor remain unchanged.

| Field | Required behaviour |
| --- | --- |
| anchor | Must exactly match a source paragraph anchor such as P014. |
| role | Use one concise sentence to explain where the passage sits in the paper: defines, motivates, specifies a method, reports evidence, qualifies a claim, and so on. It is navigation, not the main note. |
| context | Name the concrete idea inherited from nearby text and the concrete question, method, result, or claim that this passage prepares. Do not write an empty phrase such as “connects the previous and next text.” |
| explanation | This is the main teaching text. In deep mode, write 2–4 connected Chinese sentences (normally at least 100 non-whitespace characters) that explain the actual content for a reader new to the field: what the author means, how the reasoning works, unfamiliar terms, and why the point matters. Do not turn it into a “purpose / link / key point” outline. |
| takeaway | State the plain-language conclusion the reader should retain after understanding the passage. |
| caveat | State a source-grounded ambiguity, boundary, or explicitly say that no additional caveat is needed. |
| translation | A faithful Chinese translation only when full-translation mode is selected; otherwise an empty field. |
| focus_points | In deep mode, provide 1–3 exact important sentences or short phrases from the same source paragraph. Each point supplies a left-side highlight and a separate beginner-facing close-reading explanation. This optional, backward-compatible field never changes the stable paragraph anchor. |

## Non-negotiable checks

1. Every extracted paragraph must receive exactly one annotation.
2. No annotation may target an anchor that does not exist in the source.
3. The renderer must show the same anchor in the source and note columns.
4. Notes must distinguish author claims from the reader-facing explanation.
5. Unsupported interpretation must be placed in caveat or omitted.
6. In deep mode, a short page-role summary cannot be saved as an explanation.
7. Every focus-point quote must be copied from its own anchored source paragraph; unmatched or duplicate quotes are rejected instead of silently rendered in the wrong place.

## Formula and notation markup

When an explanation needs a formula, use TeX-style delimiters in the existing
`explanation`, `context`, or `takeaway` text fields. This does **not** change
the public annotation schema.

- Inline notation: `\(R_{i,t}=\Delta^{ad}_{i,t}C_i\)`
- A standalone formula: `\[\frac{a+b}{c}\]`

The HTML renderer writes browser-native MathML and the DOCX renderer writes
editable Office Math for common variables, Greek letters, subscripts,
superscripts, fractions, operators, and `\mathrm` / `\text` / `\mathcal`.
The explanation must also say what each important symbol means and why the
formula is being introduced. Complex PDF equation reconstruction is still
limited by the text extracted from the source PDF, so the original paper
remains authoritative.

For a formula focus point, additionally supply `formula_latex` without the
delimiters, for example `R_{i,t}=\Delta^{ad}_{i,t}C_i`. Its close-reading
explanation must explain the symbols, what changes when a term increases or
decreases, and one small numerical example. This turns a displayed equation
into an idea that a reader new to the field can reason about.

## Source-side stopping points

The HTML reading copy is deliberately original-first. It keeps the original
paragraph on the left and, when full translation is selected, places the
Chinese translation immediately below it. It can switch among original only,
translation only, and the paired view.

Important source quotations are highlighted in the left column. Selecting one
opens its matching right-side teaching card. Readers can also select any other
sentence in the left column and copy a prefilled follow-up request for the
current ChatGPT conversation; the App then retrieves that sentence's paragraph
and immediate context before explaining it. A standalone downloaded HTML file
cannot itself call the ChatGPT model, so the final on-demand explanation is
written in the ChatGPT conversation rather than hidden in the browser.

## What good looks like

Weak note:

> 作用：这一页介绍模型，并引出后文。

Useful note:

> 作者在这里不是泛泛地“介绍模型”，而是把前面提出的实际问题变成可计算的对象：哪些量由系统观察、哪些量由方法决定、结果会用什么标准衡量。前一段已经说明为什么原有做法不够，这一段则给出后续方法和结果都要使用的共同语言。对零基础读者来说，先把这些变量理解为“系统状态的记账方式”，不要把它们误当成已经得到的结论；后面的比较正是依赖这些定义来判断方案是否更好。

## Quality boundary for v0.1

The tool checks correspondence and required fields automatically. It cannot
prove that a model's academic interpretation is correct. Readers should inspect
the original source and treat notes as reading support, not as a replacement for
the paper.
