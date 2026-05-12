with open(r'd:\Project\QAScorer\qa_scorer.py', 'rb') as f:
    raw = f.read()

source = raw.decode('utf-8')
lines = source.split('\n')

# Try each line from 95 to 110
for end in range(95, 115):
    test_source = '\n'.join(lines[:end])
    try:
        compile(test_source, 'test.py', 'exec')
        print(f"Lines 1-{end}: OK")
    except SyntaxError as e:
        print(f"Lines 1-{end}: SyntaxError at reported line {e.lineno}: {e.msg}")
        if e.text:
            print(f"  Text: {e.text.strip()}")
