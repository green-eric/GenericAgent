import sys
print("Python:", sys.version)
f = open(r'd:\Project\QAScorer\qa_scorer.py', 'rb')
raw = f.read()
f.close()
# Check for BOM
print("First 3 bytes:", raw[:3].hex())
# Check line 115 area
lines = raw.split(b'\n')
for i in range(113, 120):
    line = lines[i]
    print(f"Line {i+1}: {line[:80]}")
    # Check if there are any non-ASCII bytes that might be misinterpreted
    try:
        line.decode('ascii')
    except UnicodeDecodeError:
        print(f"  -> Non-ASCII bytes at positions: {[j for j,b in enumerate(line) if b > 127]}")
