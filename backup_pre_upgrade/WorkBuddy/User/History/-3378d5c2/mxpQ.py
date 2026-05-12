# Read the file and check encoding issues
with open(r'd:\Project\QAScorer\qa_scorer.py', 'rb') as f:
    raw = f.read()

# Check first line for coding declaration
first_line = raw.split(b'\n')[0]
print("First line:", first_line)

# Try to find the problematic byte sequence around line 115
lines = raw.split(b'\n')
line115 = lines[114]
print(f"\nLine 115 ({len(line115)} bytes):")
for i in range(0, len(line115), 16):
    chunk = line115[i:i+16]
    hex_str = ' '.join(f'{b:02x}' for b in chunk)
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print(f"  {i:4d}: {hex_str}  {ascii_str}")

# Check if there's a BOM or other marker
print(f"\nFile starts with: {raw[:10].hex()}")

# Try decoding line 115
try:
    decoded = line115.decode('utf-8')
    print(f"\nDecoded line 115: {repr(decoded)}")
except Exception as e:
    print(f"\nDecode error: {e}")

# Check if file has correct UTF-8 BOM
if raw[:3] == b'\xef\xbb\xbf':
    print("Has UTF-8 BOM")
else:
    print("No UTF-8 BOM")

# Try reading with explicit encoding
try:
    with open(r'd:\Project\QAScorer\qa_scorer.py', 'r', encoding='utf-8-sig') as f:
        lines2 = f.readlines()
    line115_2 = lines2[114]
    print(f"\nWith utf-8-sig: {repr(line115_2.rstrip())}")
except Exception as e:
    print(f"utf-8-sig error: {e}")
