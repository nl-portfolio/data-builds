# Findings Summary: Healthcare Ops & Finance (SPARCS Inpatient 2024)

*Read the way a health insurer would read it. Based on 143,613 real,
de-identified inpatient discharges across 24 facilities and 14 counties in New
York's Capital/Adirondacks region, 2024 ($2.27bn in inpatient cost). Full
method, data, and caveats live in the rest of `docs/`.*

**Bottom line.** Spending is heavily concentrated in a small number of very
sick patients and a short list of conditions, while the region's financial and
access risk sits with its small rural hospitals, several of which are both
Medicaid-dependent and low-volume. The urban core and rural periphery differ
less in how sick patients are than in how they reach care.

### 1. Where is the money concentrated?

Very concentrated. The most severe ("Extreme") tier of cases is under 10% of
admissions but drives 24.7% of total cost. At the patient level it is starker:
the most expensive 1% of admissions account for about 11% of spend, the top 5%
for about 28%, and the top 10% for about 40%. A few conditions lead the bill,
with serious infections and septicemia the single largest driver (about
$221M), and roughly the top 100 of 324 condition groups cover about 80% of
cost. **So what:** care-management effort should target a narrow band of
high-severity cases and a handful of conditions, not spread evenly across the
book.

### 2. How do hospital charges compare to costs?

Regionwide, hospitals bill about **$2.95 in charges for every $1 of estimated
cost**, below both national reference points (about 3.1 and about 3.4). The
spread is wide, from about 4.8x at the high end (Saratoga) to near 1:1
(O'Connor). **Read with care:** the "cost" figure is estimated by the state
from charges, so this ratio mostly reflects each hospital's assigned
cost-to-charge factor rather than an independent pricing decision. Treat it as
a directional flag for contract review, not proof of aggressive pricing.

### 3. Who pays, and where is Medicaid exposure highest?

Government payers (Medicare, Medicaid, and similar) cover **about 65% of
discharges**. Medicaid specifically is at least 16.4% and, once the region's
large "managed care, unspecified" bucket is accounted for, more realistically
**about 24% (up to 27%)**. Medicaid concentration is highest at small rural and
specialty facilities, where several rural hospitals run 85 to 95%
government-paid. **So what:** the facilities most exposed to Medicaid funding
changes are also the smallest and least financially resilient, which puts the
region's hospital coverage at risk for an insurer and is not just a hospital
problem.

### 4. Do patients stay longer in some places?

The typical stay is short, with a median of 3 days and an average of 5.5, and
length of stay rises sharply with severity (the sickest patients at the
academic center stay 12 to 16 days). Holding severity constant, rural regions
show *shorter* stays for the most severe cases (about 7.6 versus about 12.6
days for Extreme cases in the Mohawk Valley versus the Capital District).
**So what:** shorter severe-case stays in rural areas most likely reflect
limited on-site capacity and transfers out, pointing to post-acute and
specialty access gaps rather than more efficient care.

### 5. How does the urban core differ from the rural periphery?

The clearest difference is the *route into the hospital*, not how sick patients
are (severity mix is similar region to region). About 62% of all admissions
start in the ER, but that rises to about 72% in the Mohawk Valley, which also
has the lowest inpatient use per resident. **So what** (a signal to
investigate, not a settled fact, since patients travel across county lines):
residents of the most constrained rural sub-region appear to reach inpatient
care disproportionately through the ER rather than through planned care,
consistent with limited non-emergency access, and worth checking whether the
region has enough non-emergency hospital capacity.

### Which facilities to watch

Combining Medicaid dependency, case complexity, and size into one risk signal
(general-acute hospitals only) puts **Ellis** and **Nathan Littauer** at the
top. Nathan Littauer is the clearest case: a genuine rural hospital with real
volume, a high Medicaid mix (about 30%), and limited financial cushion, making
it the first place an insurer should watch to be sure the region keeps enough
hospital coverage.

---
*Every figure above is validated against the source data; see
`docs/decisions.md` and `docs/review_findings_and_fixes.md` for derivations,
sensitivity ranges, and the honest limits of each metric.*
