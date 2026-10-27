import argparse
import json
import re
from pathlib import Path

TOKEN = re.compile(
    r"""//[^\n]*|/\*.*?\*/|(?:u8|u|U|L)?"(?:\\.|[^"\\])*"(?:_q)?|(?:u|U|L)?'(?:\\(?:x[0-9a-fA-F]+|u[0-9a-fA-F]{4}|.)|[^'\\])'|[A-Za-z_]\w*|::|->|[^\s]""",
    re.S,
)
METHODS = {
    "addControl",
    "addButton",
    "addSectionButton",
    "addPremiumButton",
    "addPrivacyButton",
    "addCheckbox",
    "addSubsectionTitle",
}


def tokens(source):
    source = re.sub(r"(?ms)^\s*#if\s+0\s*\n.*?^\s*#endif[^\n]*", "", source)
    return [
        m.group()
        for m in TOKEN.finditer(source)
        if not m.group().startswith(("//", "/*"))
    ]


def closing(ts, start):
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for i in range(start, len(ts)):
        t = ts[i]
        if t in ("(", "[", "{"):
            stack.append(t)
        elif t in pairs:
            if not stack or stack.pop() != pairs[t]:
                raise ValueError("Unbalanced C++ delimiters")
            if not stack:
                return i
    raise ValueError("Unclosed C++ delimiter")


def split(ts):
    parts, start, i = [], 0, 0
    while i < len(ts):
        if ts[i] in ("(", "[", "{"):
            i = closing(ts, i)
        elif ts[i] == ",":
            parts.append(ts[start:i])
            start = i + 1
        i += 1
    return parts + [ts[start:]]


def literal(ts, bindings):
    if len(ts) == 1:
        if ts[0] in bindings:
            return bindings[ts[0]]
        match = re.fullmatch(r'(?:u8|u|U|L)?("(?:\\.|[^"\\])*")(?:_q)?', ts[0])
        if match:
            return json.loads(match[1])
    if ts[:4] == ["std", "::", "move", "("] and ts[-1:] == [")"]:
        return literal(ts[4:-1], bindings)
    return None


def receiver_environments(body, names, inherited):
    parameters = {}
    for i, token in enumerate(body):
        if token != "(":
            continue
        end = closing(body, i)
        b = end + 1
        while b < len(body) and body[b] in (
            "const",
            "mutable",
            "noexcept",
            "override",
            "final",
        ):
            b += 1
        if body[b : b + 1] == ["->"]:
            while b < len(body) and body[b] not in ("{", ";", "=", ")"):
                b += 1
        if body[b : b + 1] != ["{"]:
            continue
        declared = {}
        for param in split(body[i + 1 : end]):
            param = param[: param.index("=")] if "=" in param else param
            if len(param) >= 2 and param[-1] in names:
                declared[param[-1]] = "SectionBuilder" in param[:-1]
        parameters[b] = declared
    environments, stack = [], [dict(inherited)]
    parentheses = 0
    parent_scopes = []
    for i, token in enumerate(body):
        if token == "(":
            parentheses += 1
        if token == "{":
            parent_scopes.append(parentheses)
            parentheses = 0
            stack.append(dict(stack[-1]))
            stack[-1].update(parameters.get(i, {}))
        if (
            not parentheses
            and token in names
            and i > 0
            and body[i + 1 : i + 2] in ([";"], ["="], ["{"])
        ):
            start = i - 1
            while start >= 0 and body[start] in ("&", "*", "const"):
                start -= 1
            if (
                start >= 0
                and re.fullmatch(r"[A-Za-z_]\w*", body[start])
                and body[start] not in ("return", "co_return", "throw", "delete")
            ):
                stack[-1][token] = body[start] == "SectionBuilder"
        environments.append(dict(stack[-1]))
        if token == ")":
            parentheses -= 1
        if token == "}" and len(stack) > 1:
            stack.pop()
            parentheses = parent_scopes.pop()
    return environments


def scan(source, main_menu=False):
    ts = tokens(source)

    receivers = {
        ts[i + 2]
        for i, token in enumerate(ts[:-2])
        if token == "SectionBuilder" and ts[i + 1] in ("&", "*")
    }
    if not receivers and not main_menu:
        return set()

    def walk(body, bindings, depth=0, entries=False, inherited=None):
        if depth > 8:
            return set()
        result, lambdas = set(), []
        environments = receiver_environments(body, receivers, inherited or {})
        scopes = []
        scope_end = {}
        for position, token in enumerate(body):
            if token == "{":
                scopes.append(closing(body, position))
            scope_end[position] = scopes[-1] if scopes else len(body)
            if token == "}" and scopes:
                scopes.pop()
        i = 0
        while i + 4 < len(body):
            if body[i] == "auto" and body[i + 2 : i + 4] == [
                "=",
                "[",
            ]:
                capture_end = closing(body, i + 3)
                p = capture_end + 1
                if p < len(body) and body[p] == "(":
                    end = closing(body, p)
                    params = split(body[p + 1 : end])
                    names = [
                        next(
                            (
                                t
                                for t in reversed(arg)
                                if re.fullmatch(r"[A-Za-z_]\w*", t)
                            ),
                            "",
                        )
                        for arg in params
                    ]
                    b = end + 1
                    while b < len(body) and body[b] not in ("{", ";"):
                        b += 1
                    if b < len(body) and body[b] == "{":
                        stop = closing(body, b)
                        lambdas.append(
                            (
                                body[i + 1],
                                names,
                                body[b + 1 : stop],
                                stop,
                                scope_end[i],
                                environments[b],
                            )
                        )
            i += 1
        for i, t in enumerate(body):
            if (
                t in METHODS
                and i > 1
                and environments[i].get(body[i - 2], False)
                and body[i - 1] in (".", "->")
                and body[i + 1 : i + 3] == ["(", "{"]
            ):
                end = closing(body, i + 2)
                for field in split(body[i + 3 : end]):
                    if field[:3] == [".", "id", "="]:
                        value = literal(field[3:], bindings)
                        if value:
                            result.add(value)
            if entries and t == "SearchEntry" and body[i + 1 : i + 2] == ["{"]:
                end = closing(body, i + 1)
                for field in split(body[i + 2 : end]):
                    if field[:3] == [".", "id", "="]:
                        value = literal(field[3:], bindings)
                        if value:
                            result.add(value)
            if (
                t == "add"
                and i > 1
                and environments[i].get(body[i - 2], False)
                and body[i - 1] in (".", "->")
                and body[i + 1 : i + 2] == ["("]
            ):
                end = closing(body, i + 1)
                args = split(body[i + 2 : end])
                if len(args) == 2 and args[0] != ["nullptr"]:
                    result.update(
                        walk(args[1], bindings, depth + 1, True, environments[i])
                    )
            candidates = [
                item for item in lambdas if item[0] == t and item[3] < i < item[4]
            ]
            if candidates and body[i + 1 : i + 2] == ["("]:
                end = closing(body, i + 1)
                _, names, implementation, _, _, captured = candidates[-1]
                args = split(body[i + 2 : end])
                values = {
                    name: literal(arg, bindings) for name, arg in zip(names, args)
                }
                result.update(
                    walk(implementation, values, depth + 1, inherited=captured)
                )
            if main_menu and t == "addAction" and body[i + 1 : i + 2] == ["("]:
                end = closing(body, i + 1)
                args = split(body[i + 2 : end])
                if len(args) == 3:
                    value = literal(args[2], bindings)
                    if value:
                        result.add(value)
        return result

    return walk(ts, {})


def collect(root):
    result = set()
    for path in sorted((root / "settings").rglob("*.cpp")):
        result.update(scan(path.read_text(encoding="utf-8")))
    result.update(
        scan((root / "window/window_main_menu.cpp").read_text(encoding="utf-8"), True)
    )
    return sorted(result)


def generate(root, output):
    ids = collect(root)
    text = (
        "\n".join("u" + json.dumps(value, ensure_ascii=True) + "_q," for value in ids)
        + "\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists() or output.read_text(encoding="utf-8") != text:
        output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect IDs at connected settings UI sinks, not arbitrary .id fields."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.source, args.output)
