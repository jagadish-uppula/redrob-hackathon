import json
from collections import Counter
from datetime import datetime

print("Scanning full 100K candidates.jsonl...")
titles = Counter()
countries = Counter()
exp_ranges = Counter()
tiers = Counter()
open_to_work = 0
total = 0

with open(r'c:\hackathon redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl','r',encoding='utf-8') as f:
    for line in f:
        if not line.strip():
            continue
        c = json.loads(line)
        total += 1
        p = c['profile']
        titles[p['current_title']] += 1
        countries[p['country']] += 1
        yoe = p['years_of_experience']
        if yoe < 2: exp_ranges['0-2'] += 1
        elif yoe < 5: exp_ranges['2-5'] += 1
        elif yoe < 9: exp_ranges['5-9'] += 1
        elif yoe < 15: exp_ranges['9-15'] += 1
        else: exp_ranges['15+'] += 1
        
        for ed in c.get('education',[]):
            tiers[ed.get('tier','unknown')] += 1
        
        if c['redrob_signals']['open_to_work_flag']:
            open_to_work += 1

print(f'Total candidates: {total}')
print(f'Open to work: {open_to_work} ({100*open_to_work/total:.1f}%)')

print('\n=== TOP 30 TITLES ===')
for t, n in titles.most_common(30):
    print(f'  {t}: {n} ({100*n/total:.1f}%)')

print(f'\n=== TOTAL UNIQUE TITLES: {len(titles)} ===')

print('\n=== COUNTRY DISTRIBUTION ===')
for t, n in countries.most_common(10):
    print(f'  {t}: {n} ({100*n/total:.1f}%)')

print('\n=== EXPERIENCE RANGE ===')
for r in ['0-2','2-5','5-9','9-15','15+']:
    if r in exp_ranges:
        print(f'  {r}y: {exp_ranges[r]} ({100*exp_ranges[r]/total:.1f}%)')

print('\n=== EDUCATION TIER ===')
for t, n in tiers.most_common():
    print(f'  {t}: {n}')

# AI-relevant titles
ai_kw = ['AI','ML','Machine Learning','Data Scientist','Data Engineer','NLP',
         'Search Engineer','Recommendation','Backend Engineer','Software Engineer',
         'Full Stack','DevOps','Cloud Engineer','Platform Engineer']
print('\n=== AI/TECH-RELEVANT TITLE COUNTS ===')
for kw in ai_kw:
    count = sum(n for t,n in titles.items() if kw.lower() in t.lower())
    print(f'  Contains "{kw}": {count}')
