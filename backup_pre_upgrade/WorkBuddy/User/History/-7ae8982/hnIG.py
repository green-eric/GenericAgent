import sys

with open(r'd:\Project\QAScorer\qa_scorer.py', 'rb') as f:
    raw = f.read()

print(f"File size: {len(raw)} bytes")
print(f"First 20 bytes hex: {raw[:20].hex()}")

# Try decoding as UTF-8
try:
    source = raw.decode('utf-8')
    print(f"UTF-8 decode OK, {len(source)} chars")
except Exception as e:
    print(f"UTF-8 decode failed: {e}")
    sys.exit(1)

# Try compiling
try:
    compile(source, 'qa_scorer.py', 'exec')
    print("Compilation OK!")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    print(f"  Text: {e.text}")
    
    # Show surrounding lines
    lines = source.split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+2)):
        marker = ">>>" if i == e.lineno-1 else "   "
        print(f"{marker} {i+1}: {lines[i]}")
