# Binary search for the syntax error
with open(r'd:\Project\QAScorer\qa_scorer.py', 'rb') as f:
    raw = f.read()

source = raw.decode('utf-8')
lines = source.split('\n')
total = len(lines)

# Try compiling progressively more lines
lo, hi = 100, 120
while lo < hi:
    mid = (lo + hi) // 2
    test_source = '\n'.join(lines[:mid])
    try:
        compile(test_source, 'test.py', 'exec')
        lo = mid + 1  # no error, try more
    except SyntaxError as e:
        hi = mid  # error found, narrow down

# Now lo should be near the error
print(f"Error around line {lo}")
for i in range(max(0, lo-5), min(total, lo+3)):
    marker = ">>>" if i == lo-1 else "   "
    print(f"{marker} {i+1}: {lines[i]}")
