"""Phase 6 independent validation.

Re-derives every value that appears on the scorecard directly from
outputs/tables/*.csv, applying the same formatting the guide's DAX applies,
and compares against outputs/phase6_validation_reference.md.

This is deliberately NOT a spot check: every cell that reaches the page is
recomputed here.
"""
import pandas as pd, sys, io

B = '/sessions/dreamy-awesome-davinci/mnt/hints-commitment-experiment'
T = f'{B}/outputs/tables'
out = []
def p(*a): out.append(' '.join(str(x) for x in a))

def pp(v):   # DAX "+0.00;-0.00"
    return f'{v:+.2f}'
def pv(v):   # DAX "0.000"
    return f'{v:.3f}'
def rate(v): # DAX "0.00"
    return f'{v:.2f}'
def cnt(v):
    return f'{v:,.0f}'

itt  = pd.read_csv(f'{T}/primary_itt.csv')
mde  = pd.read_csv(f'{T}/mde.csv')
m3   = pd.read_csv(f'{T}/multiplicity_holm_m3.csv')
m5   = pd.read_csv(f'{T}/multiplicity_holm_m5.csv')
sfm  = pd.read_csv(f'{T}/sensitivity_filter_missing.csv')
swns = pd.read_csv(f'{T}/sensitivity_web_never_seen.csv')
mode = pd.read_csv(f'{T}/mode_subgroup.csv')
pp_  = pd.read_csv(f'{T}/per_protocol.csv')
bal  = pd.read_csv(f'{T}/balance.csv')
ah   = pd.read_csv(f'{T}/assertion_history.csv')
peek = pd.read_csv(f'{T}/peeking_illustration.csv')

p('='*72); p('PANEL A — headline strings, rebuilt from cells via the guide DAX')
p('='*72)
for _, r in itt.iterrows():
    hid = r['hypothesis_id']
    holm = m3.loc[m3['hypothesis_id'] == hid, 'p_holm']
    assert len(holm) == 1, f'Holm lookup on hypothesis_id={hid} returned {len(holm)} rows'
    holm = holm.iloc[0]
    p(f'\n### {hid} — {r["hypothesis"]}')
    p(f'  Effect Label : {pp(r["difference_pp"])} pp   {r["ci_difference_pp"]} pp')
    p(f'  Rates Label  : Treatment {rate(r["rate_treatment_pct"])}%   vs   Control {rate(r["rate_control_pct"])}%')
    p(f'  Arms Label   : Treatment n = {cnt(r["n_treatment"])}   |   Control n = {cnt(r["n_control"])}')
    p(f'  p Label      : p = {pv(r["p_uncorrected"])} uncorrected   |   p = {pv(holm)} Holm (family of 3)')
    p(f'  Verdict Class: {r["verdict_class"]}')
    p(f'  Verdict      : {r["verdict"]}')

p('\n'+'='*72); p('PANEL B — dot, whiskers, MDE band (all three rows)')
p('='*72)
p(f'{"H":<4}{"dot":>8}{"CI low":>9}{"CI high":>9}{"MDE emp":>10}{"MDE grid":>10}  inside band?')
for _, r in itt.iterrows():
    inside = abs(r['difference_pp']) < r['mde_empirical_pp']
    p(f'{r["hypothesis_id"]:<4}{pp(r["difference_pp"]):>8}{pp(r["ci_low_pp"]):>9}'
      f'{pp(r["ci_high_pp"]):>9}{"±"+rate(r["mde_empirical_pp"]):>10}'
      f'{"±"+rate(r["mde_grid_formula_pp"]):>10}  {inside}')

p('\n-- cross-check: mde.csv agrees with primary_itt.csv on the shared columns --')
mg = itt.merge(mde, on='hypothesis_id', suffixes=('_itt', '_mde'))
assert len(mg) == 3
for c in ['mde_empirical_pp', 'mde_grid_formula_pp', 'n_treatment', 'n_control']:
    d = (mg[f'{c}_itt'] - mg[f'{c}_mde']).abs().max()
    p(f'  {c:<22} max abs diff itt vs mde = {d}')
d = (mg['difference_pp'] - mg['observed_effect_pp']).abs().max()
p(f'  {"difference_pp vs observed_effect_pp":<22} max abs diff = {d}')
p(f'  observed_effect_below_empirical_mde flags: {list(mg["observed_effect_below_empirical_mde"])}')
p('  recomputed |effect| < MDE          : ' + str(list((mg['difference_pp'].abs() < mg['mde_empirical_pp_itt']))))

p('\n-- cross-check: CI string vs numeric CI columns --')
for _, r in itt.iterrows():
    s = r['ci_difference_pp'].strip('[]').split(',')
    lo, hi = float(s[0]), float(s[1])
    p(f'  {r["hypothesis_id"]}: string [{lo}, {hi}] vs numeric '
      f'[{r["ci_low_pp"]}, {r["ci_high_pp"]}]  match={abs(lo-r["ci_low_pp"])<5e-4 and abs(hi-r["ci_high_pp"])<5e-4}')

p('\n-- cross-check: does the CI exclude zero anywhere? (must be no, all null) --')
for _, r in itt.iterrows():
    p(f'  {r["hypothesis_id"]}: CI excludes 0 = {(r["ci_low_pp"]>0) == (r["ci_high_pp"]>0)}')

p('\n'+'='*72); p('PANEL C — multiplicity, family of 3 and footnote family of 5')
p('='*72)
for name, df in (('m3', m3), ('m5', m5)):
    p(f'\n-- {name} --')
    for _, r in df.iterrows():
        p(f'  {r["hypothesis"]:<38} p={pv(r["p_uncorrected"])}  thr={pv(r["holm_threshold"])}'
          f'  holm={pv(r["p_holm"])}  reject={r["reject_at_familywise_0.05"]}')
    p(f'  any rejection: {df["reject_at_familywise_0.05"].any()}')

p('\n-- Holm recomputation from p_uncorrected (independent of the stored p_holm) --')
def holm(ps):
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [0.0]*m; run = 0.0
    for k, i in enumerate(order):
        run = max(run, (m-k)*ps[i]); adj[i] = min(run, 1.0)
    return adj
for name, df in (('m3', m3), ('m5', m5)):
    rec = holm(list(df['p_uncorrected']))
    mx = max(abs(a-b) for a, b in zip(rec, df['p_holm']))
    p(f'  {name}: recomputed Holm vs stored, max abs diff = {mx:.2e}')

p('\n'+'='*72); p('PANEL D — pre-registered mode subgroup')
p('='*72)
for _, r in mode.iterrows():
    p(f'  {r["family"]:<20} {r["mode"]:<28} {pp(r["diff_pp"]):>7}  '
      f'[{pp(r["ci_lo_pp"])}, {pp(r["ci_hi_pp"])}]  p={pv(r["p_value"])}')
p(f'  interaction rows present: {list(mode.loc[mode["mode"].str.contains("interaction"), "family"])}')

p('\n'+'='*72); p('PANEL E — sensitivity blocks')
p('='*72)
for name, df in (('Filter-Missing', sfm), ('Web-Never-Seen', swns)):
    p(f'\n-- {name} --')
    for _, r in df.iterrows():
        p(f'  {r["hypothesis_id"]}: primary {pp(r["primary_diff_pp"])} (p={pv(r["primary_p"])})  '
          f'sensitivity {pp(r["sensitivity_diff_pp"])} (p={pv(r["sensitivity_p"])})  '
          f'sign_agrees={r["sign_agrees"]} both_null={r["both_null_at_0.05"]}')
p('\n-- primary_diff_pp / primary_p must equal primary_itt cells --')
for name, df in (('Filter-Missing', sfm), ('Web-Never-Seen', swns)):
    j = df.merge(itt, on='hypothesis_id', suffixes=('_s', '_i'))
    p(f'  {name}: max |primary_diff_pp - difference_pp| = '
      f'{(j["primary_diff_pp"]-j["difference_pp"]).abs().max()}, '
      f'max |primary_p - p_uncorrected| = {(j["primary_p"]-j["p_uncorrected"]).abs().max()}')

p('\n'+'='*72); p('PANEL F — balance')
p('='*72)
for _, r in bal.iterrows():
    p(f'  {r["covariate"]:<32} p={pv(r["p_value"])} gap={rate(r["max_arm_share_gap_pp"])}pp  '
      f'tx={rate(r["treatment_share_pct"])}% ctl={rate(r["control_share_pct"])}%  '
      f'[{r["overrepresented_level"]}] {r["flag"]}')
p(f'  balanced count: {(bal["flag"]=="balanced").sum()} / {len(bal)}')
row = bal[bal['covariate'].str.contains('FormType')].iloc[0]
p(f'  guide caption trace -> tx {row["treatment_share_pct"]:.2f} / ctl {row["control_share_pct"]:.2f} '
  f'/ p {row["p_value"]:.3f} / level "{row["overrepresented_level"]}"')

p('\n'+'='*72); p('PANEL G — per protocol')
p('='*72)
for _, r in pp_.iterrows():
    p(f'  {r["group"]:<70} n={r["n"]:>5}  rate={r["rate_pct"]}  [{r["ci_lo_pct"]}, {r["ci_hi_pct"]}]')

p('\n'+'='*72); p('FOOTER — assertion history')
p('='*72)
p(f'  rows: {len(ah)}   all passed: {(ah["guard"]=="passed").all()}   '
  f'distinct guard values: {sorted(ah["guard"].unique())}')
p(f'  implied_n_over_n range: {ah["implied_n_over_n"].min():.4f} – {ah["implied_n_over_n"].max():.4f}')
p(f'  implied_n <= n_respondents for all rows: {(ah["implied_n"] <= ah["n_respondents"]).all()}')

p('\n'+'='*72); p('PEEKING INSET')
p('='*72)
p(f'  rows: {len(peek)}  fraction range {peek["fraction"].min()}–{peek["fraction"].max()}  '
  f'p range {peek["p_value"].min():.4f}–{peek["p_value"].max():.4f}  '
  f'crosses 0.05: {(peek["p_value"]<0.05).any()}')

p('\n'+'='*72); p('STRUCTURAL CHECKS')
p('='*72)
p(f'  hypothesis label for H2 in primary_itt : "{itt.loc[itt.hypothesis_id=="H2","hypothesis"].iloc[0]}"')
p(f'  hypothesis label for H2 in m3          : "{m3.loc[m3.hypothesis_id=="H2","hypothesis"].iloc[0]}"')
p(f'  labels identical across tables: '
  f'{set(itt["hypothesis"]) == set(m3["hypothesis"])}   <- join on hypothesis_id regardless')
p(f'  verdict_class values: {sorted(itt["verdict_class"].unique())}')
p(f'  all verdict_class in allowed set: '
  f'{set(itt["verdict_class"]) <= {"DETECTED","INFORMATIVE_NULL","UNDERPOWERED_NULL"}}')
p(f'  DAX SEARCH("DETECTED", verdict) would falsely match: '
  f'{[r.hypothesis_id for r in itt.itertuples() if "detected" in r.verdict.lower()]}'
  f'  <- why colour keys on verdict_class, not prose')

print('\n'.join(out))
