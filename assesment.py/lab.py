import json
import re
import sys
import urllib.error
import urllib.request

TARGET = (3, 11)

# Used when no file argument is given. Replace with your own lines.
DEFAULT_INPUT = """
requests==2.31.0
django==6.0
numpy==1.21.6
flask==3.0.0
langchain-pdf-agent==0.1.0
"""


def vtuple(s):
    return tuple(int(p) for p in re.findall(r"\d+", s))


def parse(line):
    m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([\w.]+)\s*$", line)
    if not m:
        raise ValueError(f"Cannot parse: {line!r}")
    return m.group(1), m.group(2)


def fetch(name, version):
    """Return requires_python string, or None if package/version is not on PyPI."""
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.load(r)["info"].get("requires_python") or ""
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def satisfies(spec, target):
    """Check a requires_python string like '>=3.8,<3.11' against target."""
    for part in filter(None, (p.strip() for p in spec.split(","))):
        m = re.match(r"(>=|<=|==|!=|>|<)\s*([\d.*]+)", part)
        if not m:
            continue
        op, ver = m.groups()
        if "*" in ver:
            prefix = vtuple(ver)
            match = target[: len(prefix)] == prefix
            if (op == "==" and not match) or (op == "!=" and match):
                return False
            continue
        v = vtuple(ver)
        n = max(len(v), len(target))
        v, t = v + (0,) * (n - len(v)), target + (0,) * (n - len(target))
        ok = {">=": t >= v, "<=": t <= v, "==": t == v,
              "!=": t != v, ">": t > v, "<": t < v}[op]
        if not ok:
            return False
    return True


def min_python(spec):
    """Largest '>=' lower bound in requires_python."""
    best = ()
    for m in re.finditer(r">=\s*([\d.]+)", spec or ""):
        best = max(best, vtuple(m.group(1)))
    return best


def check(lines):
    checked = not_found = incompatible = 0
    highest, highest_name = (), None
    for line in lines:
        name, ver = parse(line)
        checked += 1
        req = fetch(name, ver)
        if req is None:
            not_found += 1
            continue
        if req and not satisfies(req, TARGET):
            incompatible += 1
        lo = min_python(req)
        if lo > highest:
            highest, highest_name = lo, f"{name}=={ver}"
    print(f"Dependencies checked: {checked}")
    print(f"Not found on PyPI: {not_found}")
    print(f"Incompatible with Python 3.11: {incompatible}")
    if highest_name:
        print(f"Highest requirement: {highest_name} >= {'.'.join(map(str, highest))}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            text = f.read()
    else:
        text = DEFAULT_INPUT
    check([l for l in text.splitlines() if l.strip()])