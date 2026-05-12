import py_compile
import sys

try:
    py_compile.compile(r'd:\Project\QAScorer\qa_scorer.py', doraise=True)
    print("Compilation OK!")
except py_compile.PyCompileError as e:
    print(f"Compile error: {e}")
    sys.exit(1)
