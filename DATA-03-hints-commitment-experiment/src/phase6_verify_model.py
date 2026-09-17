"""Phase 6 build verification: the model against docs/powerbi_guide.md sections 6 and 7."""
import json, glob, re, os, sys
SM='HINTS7-Commitment-Scorecard.SemanticModel'; RP='HINTS7-Commitment-Scorecard.Report'
fails=[]; oks=[]
def chk(c,msg): (oks if c else fails).append(msg)

for f in (glob.glob('**/*.json',recursive=True)+glob.glob('*.pbip')
          +[f'{SM}/definition.pbism',f'{RP}/definition.pbir',f'{SM}/.platform',f'{RP}/.platform']):
    try: json.load(open(f)); chk(True,f'valid JSON: {f}')
    except Exception as e: chk(False,f'INVALID JSON {f}: {e}')

tabdir=f'{SM}/definition/tables'
tabs={os.path.basename(p)[:-5]: open(p,encoding='utf-8').read() for p in glob.glob(f'{tabdir}/*.tmdl')}
allt='\n'.join(tabs.values())+open(f'{SM}/definition/model.tmdl',encoding='utf-8').read()
m=tabs['_Measures']
expr='\n'.join(l for l in m.split('\n') if not l.strip().startswith('///'))

chk('relationship ' not in allt, 'no relationships declared (guide 1/2: tables stay unrelated)')
for b in ['ALLSELECTED','ALLEXCEPT','SUMX','AVERAGEX','FILTER (','RANKX','ALL (','ALL(','EARLIER']:
    chk(b not in expr, f'no {b.strip()} in any measure (DATA-01 ALL/ALLSELECTED scope-bug class)')
# respondent grain: the withdrawn Phase 5 unit-of-analysis risk
for src in ['analysis_frame','hints7_public','.parquet','.rda','item_denominator']:
    chk(src not in allt, f'no respondent/item-level source in the model: {src}')
locked={'primary_itt','mde','multiplicity_holm_m3','multiplicity_holm_m5','sensitivity_filter_missing',
        'sensitivity_web_never_seen','mode_subgroup','per_protocol','balance','assertion_history',
        'peeking_illustration'}
chk(set(tabs)-{'_Measures'}==locked, 'exactly the 11 locked result tables, plus _Measures')
refs=set(re.findall(r'\b([a-z_0-9]+)\[',expr))
chk(refs<=locked, f'measures reference only locked tables: {sorted(refs)}')
# arithmetic that would re-derive a statistic (POWER excluded: matches UNDERPOWERED_NULL)
chk(not re.search(r'/\s*\(|\*\s*100|SQRT\s*\(|POWER\s*\(', expr),
    'no arithmetic that re-derives a rate, SE, p-value or MDE')
chk('SEARCH' not in expr and 'FIND' not in expr, 'no SEARCH/FIND on prose (the R16 colour bug)')
chk('[Verdict Class]' in expr and 'SWITCH' in expr, 'Verdict Colour switches on verdict_class exactly')
holm=re.search(r"measure 'p \(Holm.*?lineageTag", m, re.S).group(0)
chk('hypothesis_id' in holm and 'primary_itt[hypothesis]' not in holm,
    'Holm lookup joins on hypothesis_id, never the display label')
for b in ['Effect CI (pp)','CI Low (pp)','CI High (pp)']:
    chk(f"measure '{b}'" in m, f'uncertainty companion present: {b}')
ms=tabs['mode_subgroup']
chk('{"n_tx", type number}' in ms and '{"n_tx", Int64.Type}' in ms,
    'mode_subgroup n_tx/n_ctl typed number -> Int64 (guide gap G2)')
pi=tabs['primary_itt']
exp=re.search(r'Table\.ExpandTableColumn\(Merged, "mde", \{(.*?)\}',pi).group(1)
chk(exp.count('"')==4, f'merge expands exactly 2 columns: {exp}')
chk('mde_empirical_pp"' not in exp and 'mde_grid_formula_pp"' not in exp,
    'merge does NOT expand the duplicated MDE columns (no .1 suffix ambiguity)')
chk('hypothesis_id' in re.search(r'Table\.NestedJoin\((.*?)\)',pi).group(1),
    'merge joins on hypothesis_id, never a label')
chk(m.count('\tmeasure ')==22, f'22 measures present (found {m.count(chr(9)+"measure ")})')
chk(all('summarizeBy: none' in t for k,t in tabs.items() if k!='_Measures'),
    'every data column summarizeBy: none (no accidental implicit aggregation)')
chk(len(glob.glob(f'{RP}/definition/pages/*/visuals/*/visual.json'))==0,
    'report ships as an empty page; no visual can define a forbidden slicer')

print('PASS %d / %d' % (len(oks), len(oks)+len(fails)))
for o in oks: print('  ok   ', o)
for f_ in fails: print('  FAIL ', f_)
sys.exit(1 if fails else 0)
