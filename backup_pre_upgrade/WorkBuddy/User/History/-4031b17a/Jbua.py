with open(r'd:\Project\QAScorer\qa_scorer.py', 'rb') as f:
    raw = f.read()

source = raw.decode('utf-8')
lines = source.split('\n')

# Check line 115 character by character
line115 = lines[114]
print(f"Line 115 length: {len(line115)} chars")
for i, ch in enumerate(line115):
    cp = ord(ch)
    if cp > 127 or cp < 32:
        print(f"  pos {i}: U+{cp:04X} ({ch!r})")
    elif cp == 32:
        pass  # skip spaces
    else:
        print(f"  pos {i}: U+{cp:04X} '{ch}'")

# Also check if there's something wrong with line 114
line114 = lines[113]
print(f"\nLine 114: {line114!r}")
for i, ch in enumerate(line114):
    cp = ord(ch)
    if cp > 127:
        print(f"  pos {i}: U+{cp:04X} ({ch!r})")

# Check for zero-width chars in entire file
print("\nSearching for zero-width / unusual chars...")
for i, ch in enumerate(source):
    cp = ord(ch)
    if cp in (0x200B, 0x200C, 0x200D, 0xFEFF, 0x00A0, 0x200E, 0x200F):
        line_num = source[:i].count('\n') + 1
        print(f"  Found U+{cp:04X} at line {line_num}, pos {i}")
