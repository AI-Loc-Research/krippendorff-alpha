## 1. How to compare labels with others: the basics

### There are two different questions

**Question A, reliability: do two careful people agree?**
You and the other mentee read the same 25 scenarios with the same rules. If you often disagree, the **rules (the codebook) are unclear**, and nobody's labels can be trusted, the LLM's included. Neither of you is "the right one" here; you're checking each other.

> This is what **agreement statistics** measure: percent agreement, Cohen's kappa, **Krippendorff's alpha**.

**Question B, validity: is the LLM right?**
To say whether the LLM is right, you need an **answer key**. In your study, the answer key is made in the meeting with the other mentee: wherever you two disagree, you discuss it and agree one final label. Those final labels are the **consensus**, also called the **gold standard**. Then you grade the LLM against it, like checking a student's test.
> This is what a **confusion matrix**, **precision** and **recall** measure.


### The full process, step by step

| Step | What happens | Measure | Status |
|---|---|---|---|
| 1 | Each person labels the 25 scenarios alone | — | Done (you); the other mentee? |
| 2 | Compare your labels with the other mentee's | Percent agreement + **Krippendorff's α** per component | After both finish |
| 3 | Meeting: discuss each disagreement and agree one label | Produces the **gold standard** | Your upcoming meeting |
| 4 | Compare the LLM's labels with the gold standard | **Confusion matrix, precision, recall** per component | After the meeting |

## 2. Precision and recall 
Merge your three flags into two answers, the same way the paper counts them (§2.2.4):
- **"Present"** = Clear or Ambiguous
- **"Missing"** = Not specified

Then, for each component, count four boxes. This table is the **confusion matrix**:

| | Gold says **Present** | Gold says **Missing** |
|---|---|---|
| **LLM says Present** | ✅ True positive (TP) | ❌ False positive (FP): the LLM saw something that isn't there |
| **LLM says Missing** | ❌ False negative (FN): the LLM missed something that is there | ✅ True negative (TN) |

- **Precision** = TP / (TP + FP): *"When the LLM says present, how often is it right?"*
- **Recall** = TP / (TP + FN): *"Of everything really present, how much did the LLM catch?"*

**Why this matters for the paper:** the headline is *"access is missing in 65.3% of scenarios"*.
- If the LLM has **low recall** for access, it often said "missing" when access was actually there, so the real gap is **smaller** than the paper claims.
- If it has **low precision**, it said "present" when access wasn't there, so the real gap is **bigger**.

So the recall for access and knowledge directly tests the paper's main claim.

#### **Write the comparison script and test it on made-up labels**
The script would:
   1. read mentees sheets, and the LLM flags (columns ending `_uncertainty` in `scenario_final_resolved.xlsx`)
   2. match rows on `paper_id` + `scenario_id`
   3. standardise spellings ("ambigous" → "Ambiguous")
   4. print α, the confusion matrices, precision and recall for each component

---

# 3. Krippendorff's alpha coefficient

**The game.** Mia and Raj each get the same 10 candies and three boxes: **Clear**, **Maybe**, **Not there**. Each sorts the candies alone. Then they compare.

| Candy | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Mia | Clear | Clear | Clear | Not | Not | Not | Not | Clear | Maybe | Not |
| Raj | Clear | Clear | Not | Not | Not | Not | Not | Clear | Not | Not |

They matched on **8 of 10**, which is **80%**. Sounds great, right?

**The catch: some matches happen by luck.** Imagine they closed their eyes and dropped candies into boxes at random, while still using the boxes as often as they usually do. They both like the "Not there" box a lot, so they'd sometimes match even with their eyes shut. Matches like that prove nothing.

**Alpha asks one question:** *"How much better did you do than luck?"*

> **alpha = 1 − (how much you disagreed) ÷ (how much you'd disagree by pure luck)**

For Mia and Raj:
- **Their disagreement:** 0.20
- **Pure-luck disagreement:** 0.54
- **alpha** = 1 − 0.20 ÷ 0.54 = **0.63**

So 80% matching becomes **α = 0.63** once luck is removed.

**What the score means:**
- **1** means they always agree: perfect.
- **0** means they're no better than eyes-closed guessing.
- **Below 0** means they're worse than guessing; something is very wrong.
- Krippendorff's rule of thumb: **0.80 or more is good**, **0.667–0.80 is okay but be careful**, **below 0.667 means the rules are too confusing**. Mia and Raj's 0.63 falls just short.

**Trick 1: the rare candy.** Now there are 10 candies where 9 are obviously "Not there" (like the knowledge component, which is usually missing). Mia and Raj both say "Not there" for those 9 and disagree only on candy 10.
- They matched **90%**, but **α = 0**.
- Why? If nearly everything is "Not there", even a blindfolded kid saying "Not there" every time would match a lot. The only hard candy was the rare one, and they disagreed on it, so they showed no skill beyond luck.

**Trick 2: all candies the same.** If every candy is obviously "Clear" and both say "Clear" every time, alpha **can't be calculated** (it's 0 ÷ 0). There was nothing hard to sort, so you can't tell whether they're skilled. This could happen with **threat source** in your 25, since it's almost always present.

---

# 3. Krippendorff's alpha, version 2: the technical version

## Definition
Krippendorff's α is a **chance-corrected coefficient of inter-coder reliability**:

> **α = 1 − D_o / D_e**

- **D_o** = **observed disagreement**, measured among values given to the same unit
- **D_e** = **expected disagreement**: what you'd see if values were paired at random, using everyone's combined value frequencies

The values to remember:
- **α = 1**: perfect reliability
- **α = 0**: agreement no better than chance
- **α < 0**: systematic disagreement

## Terminology
- **Unit:** the thing being coded, here one (scenario × component) cell. Compute α **separately for each component**, so each has 25 units.
- **Coders:** m raters. Here m = 2, or 3 if you treat the LLM as a coder.
- **Values:** the categories: Clear / Ambiguous / Not specified.
- **Reliability data matrix:** coders × units. Missing cells are allowed.
- **Pairable values:** values in units that have at least 2 codings. n = total pairable values (here 2 × 25 = 50).

## How it's computed
1. **Build the coincidence matrix.** For each unit u with m_u values, every ordered pair of values from *different* coders adds 1/(m_u − 1) to cell o_ck. With 2 coders, each unit adds one (c, k) pair and one (k, c) pair.
2. **Marginals:** n_c = Σ_k o_ck, the number of times value c was used; n = Σ_c n_c.
3. **Observed disagreement:** D_o = (1/n) · Σ_c Σ_k o_ck · δ²(c, k)
4. **Expected disagreement:** D_e = 1/(n(n − 1)) · Σ_c Σ_k n_c · n_k · δ²(c, k)
   - The **n − 1** comes from drawing pairs without replacement. It's alpha's **small-sample correction**.
5. **α = 1 − D_o / D_e**

**For nominal data** (δ² = 0 if c = k, otherwise 1), this simplifies to:
> α = [(n − 1) · Σ_c o_cc − Σ_c n_c(n_c − 1)] / [n(n − 1) − Σ_c n_c(n_c − 1)]

## Worked example (the same 10 candies)
**Coincidence matrix:**
- o_CC = 6 (units 1, 2, 8, counted in both orders)
- o_NN = 10
- o_CN = o_NC = 1 (unit 3)
- o_AN = o_NA = 1 (unit 9)

**Marginals:** n_C = 7, n_A = 1, n_N = 12, n = 20

**Calculation:**
- D_o = (1 + 1 + 1 + 1) / 20 = **0.200**
- D_e = 2 · (7·1 + 7·12 + 1·12) / (20 · 19) = 206 / 380 = **0.542**
- **α = 1 − 0.200 / 0.542 = 0.631**, against **80% raw agreement**

If you merge the flags into Present / Missing first (Clear + Ambiguous = Present), the same data gives **α = 0.604**.

## Levels of measurement (the δ² difference function)
- **Nominal:** categories with no order. δ² = 0 if c = k, otherwise 1.
- **Ordinal:** ranked categories. δ²_ck = (Σ_{g=c}^{k} n_g − (n_c + n_k)/2)². Disagreeing between neighbouring categories costs less.
- **Interval:** δ² = (c − k)²
- **Ratio:** δ² = ((c − k) / (c + k))²

**For your data**, there are three defensible choices:
- **Nominal on 3 categories:** the default.
- **Ordinal** with the order Not specified < Ambiguous < Clear: a Clear-vs-Ambiguous disagreement costs less than Clear-vs-Not-specified.
- **Nominal on the binary split** (Present / Missing): this matches how the paper counts "specified".

**Decide which one is primary before you look at results**, and report the others as sensitivity checks.

## How alpha relates to other measures
- **Percent agreement:** not corrected for chance, so it overstates reliability. Report it, but never alone (Lombard et al. 2002).
- **Cohen's κ:** estimates chance agreement from **each coder's own** value frequencies, so it treats systematic differences between coders as agreement. α (like **Scott's π**) **pools** the frequencies and assumes coders are interchangeable. For 2 coders, nominal data and no missing values, α ≈ π, differing only by the small-sample correction.
- **Why α:** it handles any number of coders, missing data, any level of measurement, and small samples (Hayes & Krippendorff 2007).

## Interpretation thresholds (Krippendorff 2004/2013)
- **α ≥ 0.800:** reliable
- **0.667 ≤ α < 0.800:** acceptable only for tentative conclusions
- **α < 0.667:** don't rely on the data
- Your plan docx uses **0.667** as the pass mark.

## Pitfalls that apply to your study
1. **Low prevalence (the kappa paradox).** When one category dominates, D_e becomes small, so a few disagreements drive α down sharply. The rare-candy example: **90% agreement, α = 0.000**. Knowledge (about 82% Not specified in the library) and access are exposed to this. **Report each component's prevalence and raw agreement next to α.** Gwet's AC1 can serve as a sensitivity check (Feinstein & Cicchetti 1990; Gwet 2008).
2. **No variation.** If every unit gets the same value from everyone, D_e = 0 and **α is undefined**. Threat source (about 99% present in the library) may hit this. Report it as "undefined, 100% agreement".
3. **Small sample.** With 25 units, one disagreement moves α a lot. **Report bootstrapped confidence intervals.** Hayes & Krippendorff's KALPHA macro does this; in Python you can resample units yourself.
4. **Reliability is not validity.** Two coders can agree and both be wrong. α between humans checks the codebook; whether the LLM is *right* is precision and recall against the gold standard. You can also compute α with the LLM as a third coder, but report it separately from the human-only α.
5. **Compute per component; don't pool.** Pooling all 7 components hides exactly the weak ones (access, knowledge) that the paper is about.

## Tools
- **Python:** the `krippendorff` package (`krippendorff.alpha(reliability_data=..., level_of_measurement="nominal")`, with coders as rows and units as columns). It isn't installed in the repo's environment yet.
- **R:** `irr::kripp.alpha`
- **SPSS / SAS:** Hayes's KALPHA macro (includes bootstrap)
