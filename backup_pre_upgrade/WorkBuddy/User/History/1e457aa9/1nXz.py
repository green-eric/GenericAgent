f = open(r'd:\Project\QAScorer\qa_scorer.py', 'rb')
raw = f.read()
f.close()

# Find line 115
lines = raw.split(b'\r\n')
line115 = lines[114]  # 0-indexed
print("Line 115 raw bytes:")
print(repr(line115))
print()

# Check for zero-width characters or other unusual chars
for i, b in enumerate(line115):
    if b > 127:
        # UTF-8 multi-byte
        pass
    elif b < 32 and b != 9:  # non-printable, not tab
        print(f"Non-printable byte at pos {i}: {b:#x}")

# Try to decode and check
try:
    decoded = line115.decode('utf-8')
    print("Decoded OK:", repr(decoded))
except:
    print("Decode failed!")

# Check surrounding context
print("\nLines 113-117:")
for i in range(112, 118):
    print(f"  {i+1}: {repr(lines[i])}")
