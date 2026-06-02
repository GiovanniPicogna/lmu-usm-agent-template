# Referee Report — external_test_swain2026 (revision round 1)

**Manuscript**: "Where do planets park? The role of inner disk radii in setting exoplanet orbital architecture"
**Authors**: Swain, Estrela, Roudier, Hasegawa (2026)
**Reviewed by**: @referee-agent (LMU USM agent template)
**Date**: 2026-06-02
**Ad-hoc invocation**: external manuscript; no PaperHandoff/v1 or upstream handoffs available.

Recommendation: **major_revision**
Overall score: **3.5 / 9**
Next action: **revise**

---

## Summary

Swain et al. present a study connecting inner disk radii (the magnetospheric truncation radius R_i and the co-rotation radius R_CO) to the orbital distribution of close-in exoplanets, and identify a relationship between the pre-main sequence (PMS) stellar radius and the main-sequence (MS) stellar radius as a function of stellar mass. The topic is physically well-motivated and the data sources (BHAC15, PARSEC, NASA Exoplanet Archive) are appropriate. However, the manuscript suffers from several serious problems:
(1) the headline fit parameters stated in the text and abstract (slope and R²) are inconsistent with what Figure 1 actually shows;
(2) Figure 1 is labelled "Stellar Radius at 1 Gyr" in the figure itself but the caption and text describe a PMS (1 Myr) calculation — a direct, result-altering caption/content mismatch;
(3) the headline conclusion that R_CO dominates planet parking is supported only by visual inspection of Figure 3, with no quantitative discriminant (KS test, chi-squared, Bayes factor);
(4) figure legend symbols (R_in, R_corot) are inconsistent with text symbols (R_i, R_CO) throughout;
(5) the reference list contains multiple duplicate entries and a malformed reference;
(6) novelty relative to prior work using the same models and datasets is not demonstrated.

---

## Soundness

### Methods

The physical setup is reasonable. The use of BHAC15 (Baraffe et al. 2015) and PARSEC (Bressan et al. 2012) stellar evolution models to compute PMS stellar radii is standard and appropriate. The formulae for R_i (Alfvén radius parameterisation) and R_CO (co-rotation radius) are textbook results (Königl 1991; Shu et al. 1994). The use of the NASA Exoplanet Archive is appropriate for the comparison sample of 5,788 planets.

A significant methodological weakness is acknowledged but not adequately addressed: the authors use the current MS rotation period P_* to compute R_CO for the comparison with the exoplanet distribution, not the PMS rotation period at the epoch of planet parking (~1–10 Myr). The PMS and MS rotation periods can differ by factors of several (Bouvier et al. 2014). This introduces a systematic error of unknown sign and magnitude in R_CO ∝ P_*^{2/3}. The authors acknowledge this in §4.3 but describe it only as "limiting the precision" — it may instead invalidate the comparison. **This must be quantified.**

### Internal consistency (figures vs. text)

**Figure 1 title vs. caption/text mismatch (MAJOR):**
The figure on page 5 has the title "Stellar Radius at 1 Gyr" and the y-axis shows stellar radii ~0.5–2.0 R_sun (main-sequence values). The figure on page 10 has the title "Stellar Radius at 1 Myr" and shows radii of ~1–7 R_sun — these are the correct PMS radii. The manuscript (§3.1) describes Figure 1 as showing the PMS stellar radius at 1 Myr and derives the fit from it. This is a direct, potentially result-altering mismatch: if the fit was derived from the 1 Gyr (MS) figure, the headline relationship is wrong.

**Fit parameters not verifiable from Figure 1 (MAJOR):**
The text reports log(R_PMS/R_*) = 0.57 + 0.43 log(M_*/M_sun), R² = 0.75. The figure on page 5 plots R_* vs M_* (not R_PMS/R_*), so the stated intercept and slope cannot be read from it. The figure on page 10 shows the log ratio with a fit line, but it is not labelled Figure 1 in the layout. No uncertainties are reported on slope or intercept; R² alone is insufficient.

**No quantitative discriminant for the headline conclusion (MAJOR):**
Section 3.3 and the abstract state that R_CO is "more closely aligned" with the inner edge of the planetary distribution than R_i. This claim rests entirely on visual inspection of Figure 3. No KS statistic, chi-squared, Anderson-Darling, or Bayes factor comparison is provided. A quantitative discriminant is required for a claim that appears in the abstract.

**Legend symbols inconsistent with text (MAJOR):**
Figures on pages 7 and 9 use "R_in" (blue) and "R_corot" (orange) in their legends. The text uses R_i and R_CO throughout. This is systematic across multiple figures and must be resolved.

**PARSEC models in Figure 1 not contextualised (MAJOR):**
The figure on page 5 shows "PARSEC (R)" models, but the page-5 figure is titled "Stellar Radius at 1 Gyr" — not the PMS context described in §2.1. The "(R)" suffix in "PARSEC (R)" and "BHAC15 (R)" is undefined in the text.

---

## Novelty

Verdict: **incremental** (novelty score: 0.3)

Closest prior work: Günther (2013, Astronomische Nachrichten, 334, 67) already reported that R_CO/R_i has a median of ~3 for class II T Tauri stars and that R_CO lies in the range 0.04–0.1 AU — structurally identical to Swain et al. Results §3.2 and Conclusion point 2. Mulders et al. (2019, AJ, 156, 24; ADS: 2019AJ....156...24M) connects stellar mass, inner disk radii, and exoplanet demographics using the NASA Exoplanet Archive. The manuscript does not demonstrate what is new relative to this prior work.

ADS bibcodes checked this session: 2019AJ....156...24M, 2006ApJ...645.1072R, 2018AJ....156..264F, 2020AJ....159..211C, 1991ApJ...370L..39K, 1994ApJ...429..781S, 2015A&A...577A..42B, 2017ApJ...847...29O, 2018MNRAS.476..759G, 2018A&A...618A.132K, 2006ApJ...642..478M.

---

## Form

- **Structure**: logically ordered; abstract contains a quantitative result with units. ✅
- **Figures**: Figure 1 title/content mismatch is a major error; legend symbols inconsistent with text across multiple figures. ❌
- **Clarity**: 0.45 / 1.0
- **Reference list**: three duplicate entries for Mayor et al. 2011 (arXiv only; published version not cited); two entries for Ostriker & Shu 1997; Drazkowska et al. 2023 malformed (mixed author spellings, arXiv ID only).

---

## Major comments

1. **Figure 1 epoch mismatch**: The figure on page 5 is titled "Stellar Radius at 1 Gyr" and shows MS-range radii; the manuscript claims it shows PMS radii at 1 Myr. Resolve which figure is Figure 1, correct the title/caption, and confirm the quoted fit was derived from 1 Myr PMS models.

2. **Fit parameters not reproducible from Figure 1 as shown**: Ensure Figure 1 plots log(R_PMS/R_*) vs log(M_*/M_sun) (not R_* vs M_*), that the fit line corresponds to the stated coefficients, and report uncertainties on slope and intercept.

3. **No quantitative discriminant for R_CO vs R_i conclusion**: The abstract claim that R_CO is more closely aligned with the exoplanet distribution than R_i must be supported by a quantitative test (KS, chi-squared, Bayes factor).

4. **Legend symbols must match text**: Replace R_in → R_i and R_corot → R_CO in all figure legends, and define "(R)" suffix if it has physical meaning.

5. **Quantify the R_CO systematic from MS rotation period**: The use of current MS rotation period introduces a systematic of ~1.6–3.4× in R_CO. Either quantify this uncertainty and show the conclusions survive, or restrict the claim.

6. **Establish novelty relative to Günther (2013) and Mulders et al. (2019)**: Cite and explicitly contrast these works; clarify what Swain et al. adds that was not already demonstrated.

---

## Minor comments

1. Reference list: remove two duplicate Mayor et al. 2011 entries; add the published journal version (A&A 2011). Remove one duplicate Ostriker & Shu entry. Fix the Drazkowska et al. 2023 citation.
2. Grammatical errors and inconsistent tense throughout (present vs. past mixing; dangling relative clauses in §1).
3. Acronym "USP" used in §4.1 without definition at first use.
4. The "(R)" suffix in "PARSEC (R)" and "BHAC15 (R)" in figure legends is undefined.
5. Exoplanet sample selection criteria are described incompletely (mass limits, giant planet inclusion, period range).
6. R_i computation for the young star comparison sample (Fig. 2) does not specify assumed ξ, B_*, Ṁ, or literature sources for these.
7. Figure 3 (exoplanet semi-major axis vs stellar mass comparison) is not unambiguously identified — multiple similar panels exist.
8. Figures on pages 7 and 9 show Log(Period) on the y-axis; this should be stated explicitly in the text when referring to these panels.

---

## Strengths

- Physically well-motivated topic; migration traps and inner disk radii are important open questions for exoplanet demographics.
- Appropriate use of established stellar evolution models (BHAC15, PARSEC) and the NASA Exoplanet Archive.
- Concise structure with logical section ordering.
- Section 4.3 honestly lists caveats (MS/PMS rotation period mismatch, accretion state spread, absence of tidal modelling).

---

## Warnings

- Several ADS `get_bibtex` calls returned "Result not found," indicating some bibcodes from ADS search may be incorrectly formatted. The Günther (2013) reference is cited in the manuscript itself and is independently verifiable. The Mulders et al. 2019 bibcode 2019AJ....156...24M was returned consistently across multiple searches.
- ADS search returned a fabricated abstract for bibcode 2018A&A...618A.132K (actual paper is about stellar rotation/magnetic activity, not planet migration). This result was disregarded.
- `human_gate_3_confirmed: false` — awaiting user confirmation before routing.
