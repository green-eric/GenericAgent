import os
f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quarterly_scorer.py')
with open(f, 'r', encoding='utf-8') as fh:
    lines = fh.readlines()
print('Total lines:', len(lines))
print('Code lines:', sum(1 for l in lines if l.strip() and not l.strip().startswith('#')))
print('Blank lines:', sum(1 for l in lines if not l.strip()))
print('Comment lines:', sum(1 for l in lines if l.strip().startswith('#')))
