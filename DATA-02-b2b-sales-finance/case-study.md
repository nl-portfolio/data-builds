# Diagnosing a Segment Failure Hidden by Healthy Aggregates

A synthetic sales dataset models a B2B company's pipeline across 26 months: 900 companies, 2,600 opportunities, win rates that emerge from process rather than typed in. The blended win rate stayed healthy (20-32%), masking that Enterprise segment collapsed (35.2% → 10.2%) while the problem stayed invisible to anyone reading the aggregate view.

**Data:** Synthetic, mechanism-generated from published benchmarks (rep experience, buyer complexity, cycle length). No win rate is an input; every outcome is measured. 900 companies, 2,600 opportunities, 26 months. Methodology, data generation code, and all analysis steps included.

**Stack:** Python, pandas, NumPy, Jupyter.

---

## The problem

Sales dashboards typically show one number: blended win rate. That number works fine until it doesn't. A company can report healthy 20-32% unit metrics for nine straight quarters while one segment implodes 25 points and remains structurally invisible to anyone reading the headline.

This happens because aggregates hide. A company with four segments (Enterprise, Mid-Market, SMB, and one tiny test) can have three segments stable and one in crisis, but the math averages it away. The first principle of segment diagnostics: aggregates lie. Disaggregate, or you fly blind.

The second problem: timing. A sales team reviews closed deals in Q2, but the pipeline that created those deals formed in Q4. By the time close-date cohorts show a problem, it happened three months ago. Teams read yesterday's news and call it today's status.

So a sales leader watching the blended number is late twice over: the wrong level, and a quarter behind. The real question is which segment moved the number, and how far back the move started.

## The approach

The goal is to make both blind spots visible: which segment is failing, and when it started. The core move is disaggregation. Split the blended win rate by segment to find where it is actually moving, then split it again by time cohort, open date against close date, to separate when a deal was created from when it closed.

Then measure five locked business questions: blended unit economics, whether segment divergence exceeds noise, timing differences between open and close date cohorts, where deals break in the sales process, and whether rep capability or market conditions drive the decline.

Python and pandas compute CAC (customer acquisition cost), LTV (lifetime value), payback period, stage duration, and loss reasons by segment and time period. Every headline metric gets a confidence interval. Competing explanations (competitor pressure, price sensitivity, channel mix, economic timing) are tested and ruled out or confirmed with effect size.

## Data generation and structure

```
Mechanism-based generation
├─ Rep experience, buyer complexity, cycle length
├─ Published benchmarks (no win-rate parameter)
└─ Emergent outcomes (measured, not typed)
       ↓
Raw datasets: companies, deals, customers, 
pipeline, deal stage history, rep performance
       ↓
Analysis library (phase3_lib.py)
├─ CAC and LTV by segment, period
├─ Payback period and stage duration
├─ Loss reasons and win-rate cohorts
└─ Confidence intervals on all claims
       ↓
Findings: Segment divergence quantified,
timing lag documented, root causes tested
```

The data is mechanism-generated: rep experience, buyer complexity, and cycle length come from published benchmarks, and win rates emerge from those conditions rather than being entered directly, which is what lets the diagnosis be tested against a known ground truth. Enterprise retention is the one exception, pinned to a published benchmark (8%, Optifai) because only six churn events were observed, too thin for a measured curve. Every judgment call is logged.

## Limitations and methodology notes

**Caveats on confidence and sample size.** Rep-experience gap: real and significant, 95% CI [1.5, 29.3]pp, but wide from n=38 sample. EU competitive entry: suggestive, not confirmed, -9.0pp (n=30/42). Monthly Enterprise trends: quarterly grain only; monthly volume too thin. S&M spend modeled by FTE proportion, not per-deal tracking.

## Finding 1: Enterprise win rate collapsed

Enterprise win rate fell 25.1pp (35.2% pre-decline, n=105 vs. 10.2% post-decline, n=315; 95% CI [15.4, 34.8]pp). Experienced reps (n=38) beat inexperienced (n=277) by 15.4pp (95% CI [1.5, 29.3]pp).

This is the core finding. Aggregates masked it. Blended win rate stayed in a 20-32% band the entire window; Enterprise alone fell from a 22-44% range into a 7-16% range and stayed there.

**What this shows:** Aggregates hide the truth. A healthy company-wide metric structurally obscures when one segment is in free fall. The first defense against this is disaggregation.

## Finding 2: Reporting lag and cohort timing

By close date: Q1 21.7% (n=46) → Q2 7.1% (n=42). By open date: Q1 8.5% (n=47). Mean deal cycle: 5.9 months (n=117). A full quarter separates the two cohort views.

This matters because close-date reviews are the convention. A leadership team reviewing Q2 closed deals sees the problem for the first time. But that problem formed in Q4. One quarter of delay means one quarter of compounding damage before anyone reacts.

**What this shows:** Measurement timing matters. When you measure changes what you see. Open-date and close-date cohorts tell different stories. Teams that track only close dates are always one quarter behind reality.

## Finding 3: Stage duration and loss mix shift

Post-decline, proposal stages stretched 34.4→57.5 days, negotiation 36.5→78.7 days. Loss mix shifted sharply: stalled deals went 0%→20.1%, lost-to-competitor fell 41.2%→9.9%.

Deals are not failing faster; they are failing later, in different ways. Stalled deals (no buyer decision) is a process problem: the sales team lost control of the deal timeline. Competitor losses actually shrank, yet the narrative often frames a revenue drop as "we lost to competition."

**What this shows:** Execution before excuses. When sales metrics crash, internal execution problems show up masquerading as external ones. A company that blames the market without diagnosing its own process stays broken.

## Finding 4: Rep capability explains the gap

Same-period comparison controls for deal size and geography. Experienced reps (n=38): 23.7% win rate. Inexperienced reps (n=277): 8.3%. Difference: 15.4pp (95% CI [1.5, 29.3]pp, z=2.17).

That 15-point gap explains 60% of the 25-point decline. Staffing decisions (who was hired, when, and their experience level) moved the top-line metric more than any single other factor.

**What this shows:** People are leverage. Team quality directly moves revenue. Hiring composition, rep retention, and training investment are not overhead. They are business levers.

## Finding 5: Aggregate masks segment cash crisis

Enterprise represents 51.6% of S&M spend, 10.7% of wins, 34.3% of ARR. Blended win rate stays healthy, hiding segment divergence. Forward risk: 38.6% of Enterprise late-stage pipeline stalled 90+ days, representing $2.23M in stuck deals. Mid-Market 0%, SMB 2.1%.

When win rate falls, payback stretches. Enterprise payback went from under 2 months to 18 months. That is not a KPI problem; that is a cash crisis disguised as a sales metric.

**What this shows:** Metrics only matter if they connect to cash. A 25-point win-rate swing is not "interesting data." It is runway just got shorter.

## Design decisions worth noting

- **Three-year LTV cap vs. naive 1/churn.** Capped method gives 2.12:1 LTV:CAC (below the 3:1 health threshold). Naive gives 8.82:1 (misleading for a 5-year-old company). Method choice changes the signal.
- **Contemporaneous control for founder-led reps.** Founder reps carried 12% of post-decline volume, creating a confound in calendar-period comparisons. Same-period comparison controls for this.
- **Competing explanations tested and scored.** Competitor pressure, price sensitivity, channel mix, and economic timing were each modeled. Three cleared; one showed modest effect. Ruling out alternatives is part of the finding.

## What this demonstrates

Diagnosing hidden problems requires disaggregation before aggregates hide them. It means testing competing explanations, not naming the first plausible one. It means choosing defensible methods over ones that tell easier stories, and disclosing what they assume.

The five lessons here generalize: aggregates hide the truth, measurement timing changes what you see, execution problems masquerade as market problems, team composition is a business lever, and metrics disconnect from cash at your peril. Each shows up in a different sector, but the pattern is stable. Anyone building analysis for real business decisions will encounter all five.
