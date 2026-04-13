import ast
from pathlib import Path


README_PATH = Path(__file__).resolve().parents[1] / "README.rst"


def _python_code_blocks(text: str):
    lines = text.splitlines()
    i = 0
    blocks = []
    while i < len(lines):
        if lines[i].strip() == ".. code:: python":
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            block = []
            while i < len(lines):
                line = lines[i]
                if line.startswith("    "):
                    block.append(line[4:])
                    i += 1
                    continue
                if not line.strip():
                    block.append("")
                    i += 1
                    continue
                break
            if block:
                blocks.append("\n".join(block).rstrip())
            continue
        i += 1
    return blocks


def test_readme_python_examples_are_valid_syntax():
    readme = README_PATH.read_text(encoding="utf-8")
    blocks = _python_code_blocks(readme)

    assert blocks, "Expected at least one Python code block in README.rst"

    for index, block in enumerate(blocks, start=1):
        ast.parse(block, filename=f"README.rst block #{index}")

