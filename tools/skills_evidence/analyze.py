import json, re, collections, itertools, sys
d = json.load(open(sys.argv[1]))
N = len(d)
def tags(r):
    return [t.strip() for t in (r.get('techStack') or '').split(',') if t.strip()]
def family(t):
    s = t.lower()
    if re.search(r'\b(bi|business intelligence|power bi|tableau|reporting|dashboards?|visuali[sz]ation)\b', s) and re.search(r'analy|developer|engineer|specialist|consultant', s):
        return 'BI analyst'
    if re.search(r'\bproduct\b', s) and re.search(r'analy', s): return 'Product analyst'
    if re.search(r'\b(financial|finance|fp&a|fp & a|investment|credit|risk|treasury)\b', s) and re.search(r'analy', s): return 'Financial/risk analyst'
    if re.search(r'\bbusiness\b', s) and re.search(r'analy', s): return 'Business analyst'
    if re.search(r'\bdata\b', s) and re.search(r'analy', s): return 'Data analyst'
    if re.search(r'analytics engineer', s): return 'Other'
    return 'Other'
FAMS = ['Data analyst','Business analyst','Financial/risk analyst','Product analyst','BI analyst','Other']
TOOLS = ['SQL','Python','Excel','Power BI','Tableau','Looker','R','dbt','Snowflake','BigQuery','Redshift','Spark','Airflow','AWS','Azure','QuickSight','G-Sheets','Metabase']
out = {}
withstack = [r for r in d if tags(r)]
out['N']=N; out['with_stack']=len(withstack)
def shares(rows):
    n = len(rows); c = collections.Counter()
    for r in rows:
        for t in set(tags(r)): c[t]+=1
    return n, c
n, c = shares(withstack)
out['overall'] = {t:(c[t], n) for t in TOOLS}
# experience split
def isentry(r): return r['experience']=='Entry Level'
for lab, f in [('entry', isentry), ('nonentry_specified', lambda r: r['experience'] in ('Mid Level','Senior','Lead / Staff')), ('not_specified', lambda r: r['experience']=='Not Specified'), ('senior_plus', lambda r: r['experience'] in ('Senior','Lead / Staff'))]:
    rows=[r for r in withstack if f(r)]; n2,c2=shares(rows)
    out['exp_'+lab]={t:(c2[t],n2) for t in TOOLS}
    out['expall_'+lab]=(sum(1 for r in d if f(r)), n2)
# family
famcount = collections.Counter(family(r['title']) for r in d)
out['famcount']=dict(famcount)
for fm in FAMS:
    rows=[r for r in withstack if family(r['title'])==fm]; n2,c2=shares(rows)
    out['fam_'+fm]={t:(c2[t],n2) for t in TOOLS}
for lab, rx in [('Marketing/growth', r'\b(marketing|growth|crm|customer|ecommerce|e-commerce)\b'), ('Analytics manager/lead', r'\b(manager|head|director|lead)\b.*analytic|analytic.*\b(manager|head|director|lead)\b')]:
    allr=[r for r in d if re.search(rx, r['title'], re.I)]
    rows=[r for r in allr if tags(r)]; n2,c2=shares(rows)
    out['cut_'+lab]={t:(c2[t],n2) for t in TOOLS}; out['cutall_'+lab]=len(allr)
out['unique_title_company']=len({(r['title'].lower(),r['company'].lower()) for r in d})
# combos
pc=collections.Counter(); tc=collections.Counter(); full=collections.Counter()
for r in withstack:
    s=sorted(set(tags(r)) & set(TOOLS))
    full[tuple(s)]+=1
    for p in itertools.combinations(s,2): pc[p]+=1
    for p in itertools.combinations(s,3): tc[p]+=1
out['pairs']=pc.most_common(15); out['triples']=tc.most_common(12); out['full']=full.most_common(15)
# bi tool count
bi = lambda r: set(tags(r)) & {'Power BI','Tableau','Looker','QuickSight','Metabase'}
cl = lambda r: set(tags(r)) & {'AWS','Azure'}
wh = lambda r: set(tags(r)) & {'Snowflake','BigQuery','Redshift','dbt','Spark','Airflow'}
out['any_bi']=sum(1 for r in withstack if bi(r))
out['any_cloud']=sum(1 for r in withstack if cl(r))
out['any_modernstack']=sum(1 for r in withstack if wh(r))
out['sql_or_python']=sum(1 for r in withstack if set(tags(r))&{'SQL','Python'})
out['sql_and_python']=sum(1 for r in withstack if {'SQL','Python'}<=set(tags(r)))
out['excel_only_spreadsheet']=sum(1 for r in withstack if set(tags(r))<= {'Excel','G-Sheets'})
out['ntags_dist']=collections.Counter(min(len(set(tags(r))),6) for r in withstack)
# AI in titles
AIRX = re.compile(r'\b(ai|a\.i\.|ml|machine learning|llm|llms|genai|gen ai|generative|artificial intelligence|gpt|nlp|prompt|agentic|agents?)\b', re.I)
ai_titles=[r['title'] for r in d if AIRX.search(r['title'])]
out['ai_title_n']=len(ai_titles)
sub=collections.Counter()
for t in ai_titles:
    for m in AIRX.findall(t): sub[m.lower()]+=1
out['ai_title_terms']=sub.most_common()
out['ai_title_samples']=ai_titles[:60]
# AI title by family
out['ai_by_fam']={fm:(sum(1 for r in d if family(r['title'])==fm and AIRX.search(r['title'])), famcount[fm]) for fm in FAMS}
# Other title keywords
kw = {'analytics engineer':r'analytics engineer','data scientist':r'data scien','marketing/growth':r'\b(marketing|growth)\b','operations':r'\boperations?\b','supply chain':r'supply chain','quant':r'\bquant','sql in title':r'\bsql\b','python in title':r'\bpython\b','experimentation/a-b':r'experiment|a/b|ab test','statistic':r'statistic','insights':r'\binsights?\b','reporting':r'\breporting\b','data quality/governance':r'data quality|governance','manager/lead/head':r'\b(manager|lead|head|director)\b'}
out['title_kw']={k:sum(1 for r in d if re.search(v,r['title'],re.I)) for k,v in kw.items()}
out['countries']=collections.Counter(r['country'] or '(blank)' for r in d).most_common(10)
out['exp']=collections.Counter(r['experience'] for r in d).most_common()
out['stack_by_exp']={e:(sum(1 for r in d if r['experience']==e and tags(r)), sum(1 for r in d if r['experience']==e)) for e,_ in out['exp']}
out['dates']=(min(r['dateScraped'] for r in d), max(r['dateScraped'] for r in d))
# other family titles sample
out['other_samples']=collections.Counter(r['title'] for r in d if family(r['title'])=='Other').most_common(40)
# country split for US/IN/GB
for cc in ['US','IN','GB']:
    rows=[r for r in withstack if r['country']==cc]; n2,c2=shares(rows)
    out['cc_'+cc]={t:(c2[t],n2) for t in TOOLS}
json.dump(out, open(sys.argv[2],'w'), indent=1, default=str)
