# SIGNAL Reaction Validation v1

## Question

Does a SIGNAL investigation help identify stocks that subsequently show more favorable price reaction than comparable stocks that were not under investigation on the same market date?

This study does not alter Detector v1.0 Candidate thresholds. It is a validation layer placed after the frozen detector.

## Design

- Evaluated timeline: 2026-06-12 to 2026-09-29.
- Universe: 28 tickers.
- Investigation episodes / SPOT_OPEN anchors: 49.
- First DEVELOPING anchors: 26.
- First ESTABLISHED anchors: 3.
- Horizons: +1, +3, +5, +10 trading sessions.
- Primary controls: eligible NO_INVESTIGATION stocks on the same market date.
- Confidence intervals: bootstrap of matched event-minus-control differences, clustered by event date.

## Primary result — SPOT_OPEN

| Horizon | Positive close | Control | +2% reached | Control | 5D-close breakout | Control | Mean end return | Control |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 38.8% | 39.0% | 20.4% | 10.0% | 28.6% | 21.6% | -0.02% | -0.28% |
| 3 | 42.9% | 40.9% | 36.7% | 30.9% | 44.9% | 39.7% | -0.19% | -0.61% |
| 5 | 44.9% | 39.0% | 51.0% | 38.1% | 57.1% | 46.3% | 0.02% | -0.59% |
| 10 | 52.1% | 42.8% | 64.6% | 53.9% | 70.8% | 60.8% | 1.34% | -0.23% |

The direction is generally favorable by +5 and +10 sessions: SPOT_OPEN has higher positive-close rate, higher +2% reaction rate, and higher 5-session closing-range breakout rate than same-date controls. The effect is modest rather than dominant.

## Favorable excursion vs adverse excursion

| Horizon | Close-MFE SIGNAL | Control | Close-MAE SIGNAL | Control |
|---:|---:|---:|---:|---:|
| 1 | -0.02% | -0.28% | -0.02% | -0.28% |
| 3 | 1.33% | 1.09% | -1.38% | -1.91% |
| 5 | 2.42% | 1.89% | -2.20% | -2.66% |
| 10 | 4.42% | 3.54% | -3.15% | -4.28% |

A less-negative MAE is favorable. On the current retrospective sample, SPOT_OPEN generally has slightly larger favorable excursion and less-severe adverse close excursion than same-date controls at the longer horizons.

## First-touch test

The first-touch test asks whether +X% is reached before -X% within the horizon. This is closer to a directional reaction question than fixed-horizon return alone.

| Horizon | +2 before -2 | Control | +3 before -3 | Control | +5 before -5 | Control |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 20.4% | 10.0% | 8.2% | 6.0% | 4.1% | 2.2% |
| 3 | 34.7% | 29.0% | 24.5% | 20.4% | 14.3% | 9.2% |
| 5 | 42.9% | 34.5% | 36.7% | 28.2% | 22.4% | 15.4% |
| 10 | 47.9% | 39.3% | 52.1% | 38.0% | 39.6% | 25.6% |

## Bootstrap evidence

Most +1 to +5 session matched differences have 95% intervals that still cross zero. Therefore the data do not justify a strong <=1-week directional-accuracy claim yet.

The SPOT_OPEN differences whose date-cluster bootstrap interval does not cross zero are:

- +1 sessions, `hit_down_5`: difference -0.0136, 95% CI [-0.0261, -0.0024].
- +1 sessions, `hit_up_2`: difference 0.1038, 95% CI [0.0096, 0.1935].
- +1 sessions, `up_before_down_2`: difference 0.1038, 95% CI [0.0079, 0.1909].
- +10 sessions, `hit_up_3`: difference 0.1445, 95% CI [0.0145, 0.2643].
- +10 sessions, `hit_up_5`: difference 0.1404, 95% CI [0.0017, 0.2631].
- +10 sessions, `up_before_down_3`: difference 0.1411, 95% CI [0.0137, 0.2611].

## Lifecycle-state transitions

- DEVELOPING has 26 first-transition anchors.
- ESTABLISHED has only 3 first-transition anchors.

The DEVELOPING results are mixed across horizons. ESTABLISHED has only three episodes, which is far too small for a reliable directional conclusion. Therefore state escalation must not yet be marketed as monotonic price-prediction confidence.

## OHLC subset

Raw OHLC was available in the retained cache for 4 tickers and 6 SPOT_OPEN episodes. This subset was used to calculate true intraday high-based MFE and low-based MAE.

This subset is useful as a calculation cross-check, but it is too small to replace the 28-ticker close-based analysis.

## Conclusion

**Status: TENTATIVE_DIRECTIONAL_INFORMATION; NOT YET ROBUST FOR A <=5 SESSION CLAIM**

SPOT_OPEN shows a generally favorable direction versus same-date controls in several reaction metrics, especially by 5-10 sessions. However most <=5-session date-cluster bootstrap intervals still cross zero. The current retrospective sample is therefore suggestive, not sufficient to claim reliable short-horizon price-direction prediction.

The correct product claim at this stage is:

> SIGNAL identifies unusual compressed-activity setups that show some favorable subsequent reaction characteristics versus same-date controls in retrospective data. Reliable short-horizon directional prediction has not yet been established.

The next decisive test is out-of-sample: freeze Methodology v1.0 Candidate and evaluate untouched data from 1 Oct 2026 onward without changing thresholds.
