"""Brace-aware check that every `t(...)` has a `t` in scope.

The previous regex split the file at top-level declarations, which drifted
whenever a file used column-0 indentation inside a function. This walks the
real brace structure instead: for each t( use, climb the enclosing blocks and
look for a binding -- `const t = useT()`, `const t = makeT(...)`, or `t` as a
parameter of the enclosing function.
"""
import io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.environ["PROJECT_ROOT"]
FILES = ["src/App.jsx", "src/components/MessageBubble.jsx",
         "src/components/VarianceChartModal.jsx",
         "src/components/ChatWindow.jsx", "src/components/VoiceInput.jsx"]

USE = re.compile(r"\bt\(['\"]|\bt\.(?:option|action|actionDesc|echo)\(")
BIND = re.compile(r"\bconst\s+t\s*=\s*(?:useT|makeT)\s*\(")
# `(t)` / `(a, t)` / `({...}, t)` in a function header
PARAM = re.compile(r"\([^()]*\bt\b[^()]*\)\s*(?:=>|\{)")


def strip_noncode(src):
    """Blank out comments and string/template bodies so braces inside them do
    not corrupt the depth count. Length is preserved so offsets stay valid."""
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if src[k] != "\n":
                    out[k] = " "
            i = j
        elif c in "'\"":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\":
                    j += 1
                j += 1
            for k in range(i + 1, min(j, n)):
                out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


bad = []
for rel in FILES:
    path = os.path.join(ROOT, "frontend", rel)
    src = io.open(path, encoding="utf-8").read()
    code = strip_noncode(src)

    # Map every offset -> stack of enclosing OPEN BRACKETS of any kind.
    # Braces alone are not enough: `const vtFilters = (t) => [ ... ]` binds t
    # through an arrow whose body is an ARRAY, so there is no brace to find.
    PAIRS = {"{": "}", "(": ")", "[": "]"}
    stack, opens = [], [None] * (len(code) + 1)
    for i, ch in enumerate(code):
        opens[i] = tuple(stack)
        if ch in PAIRS:
            stack.append(i)
        elif ch in ")]}" and stack:
            stack.pop()

    for m in USE.finditer(src):
        # Ignore uses inside comments/strings (blanked in `code`).
        if code[m.start():m.end()].strip() == "":
            continue
        pos = m.start()
        found = False
        for open_idx in reversed(opens[pos] or ()):
            # close of this block
            closer = PAIRS[code[open_idx]]
            depth, j = 0, open_idx
            while j < len(code):
                if code[j] == code[open_idx]:
                    depth += 1
                elif code[j] == closer:
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            body = src[open_idx:j]
            # Include the opening bracket itself: a param list is only
            # recognisable as `(...) =>` or `(...) {`, and the previous slice
            # stopped one character short of the token that proves it.
            header = src[max(0, open_idx - 240):open_idx + 1]
            if BIND.search(body) or PARAM.search(header):
                found = True
                break
        if not found:
            line = src[:pos].count("\n") + 1
            bad.append(f"{rel.split('/')[-1]}:{line}  {src[pos:pos+52].strip()}")

print("t() WITHOUT a binding in any enclosing scope:", len(bad))
for b in bad:
    print("   ", b)
