import json
from collections import Counter

# Analyze sample candidates
with open(r'c:\hackathon redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\sample_candidates.json','r',encoding='utf-8') as f:
    candidates = json.load(f)
print(f'Sample count: {len(candidates)}')

# Title distribution
titles = Counter(c['profile']['current_title'] for c in candidates)
print('\n=== TITLE DISTRIBUTION (sample) ===')
for t, n in titles.most_common():
    print(f'  {t}: {n}')

# Country distribution
countries = Counter(c['profile']['country'] for c in candidates)
print('\n=== COUNTRY DISTRIBUTION ===')
for t, n in countries.most_common():
    print(f'  {t}: {n}')

# Education tier distribution
tiers = Counter()
for c in candidates:
    for ed in c.get('education',[]):
        tiers[ed.get('tier','unknown')] += 1
print('\n=== EDUCATION TIER DISTRIBUTION ===')
for t, n in tiers.most_common():
    print(f'  {t}: {n}')

# Skill count distribution
skill_counts = [len(c.get('skills',[])) for c in candidates]
print(f'\n=== SKILL COUNTS ===')
print(f'  Min: {min(skill_counts)}, Max: {max(skill_counts)}, Avg: {sum(skill_counts)/len(skill_counts):.1f}')

# Relevant AI/ML title candidates
ai_titles = ['AI Engineer','ML Engineer','Data Scientist','Machine Learning Engineer',
             'Senior AI Engineer','Senior Machine Learning Engineer','Junior ML Engineer',
             'Backend Engineer','Data Engineer','Search Engineer','NLP Engineer']
ai_candidates = [c for c in candidates if c['profile']['current_title'] in ai_titles]
print(f'\n=== AI/ML-RELEVANT TITLE CANDIDATES IN SAMPLE ({len(ai_candidates)}) ===')
for c in ai_candidates:
    p = c['profile']
    rs = c['redrob_signals']
    print(f"  {c['candidate_id']}: {p['current_title']} | {p['years_of_experience']}y | {p['country']} | resp_rate={rs['recruiter_response_rate']} | open={rs['open_to_work_flag']} | notice={rs['notice_period_days']}d")

# Check for possible honeypots in sample
print('\n=== POTENTIAL HONEYPOTS (expert skills with 0 duration) ===')
for c in candidates:
    for sk in c.get('skills', []):
        if sk['proficiency'] == 'expert' and sk.get('duration_months', 1) == 0:
            print(f"  {c['candidate_id']}: skill '{sk['name']}' is expert with 0 months duration")

# Sample submission analysis
print('\n=== SAMPLE SUBMISSION ANALYSIS ===')
import csv
with open(r'c:\hackathon redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\sample_submission.csv','r',encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

sub_titles = Counter()
for row in rows:
    # Extract title from reasoning
    reasoning = row['reasoning']
    title = reasoning.split(' with ')[0].strip()
    sub_titles[title] += 1

print('Titles in sample submission top 100:')
for t, n in sub_titles.most_common():
    print(f'  {t}: {n}')

# How many AI/ML people in the sample submission?
ai_in_sub = sum(1 for t,n in sub_titles.items() if any(kw in t for kw in ['ML','AI','Data Scientist','Machine Learning']))
non_ai_in_sub = sum(n for t,n in sub_titles.items()) - ai_in_sub
print(f'\nAI/ML-titled in sample submission: {ai_in_sub}')
print(f'Non-AI-titled in sample submission: {non_ai_in_sub}')
print('\n>>> This sample submission is INTENTIONALLY BAD - it ranks HR Managers, Accountants, Marketing Managers at top!')
