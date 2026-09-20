from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import ast

app = Flask(__name__)
CORS(app)


def make_error(line, message, why, fix):
    return {
        "line": line,
        "message": message,
        "why": why,
        "fix": fix
    }


PAIRS = {
    "(": ")",
    "[": "]",
    "{": "}"
}

REVERSE_PAIRS = {
    ")": "(",
    "]": "[",
    "}": "{"
}


# =========================================================
# SYMBOL CHECKER
# =========================================================

def check_symbols(code, language):

    errors = []
    stack = []

    for line_no, line in enumerate(code.splitlines(), 1):

        i = 0
        quote = None
        escaped = False
        block_comment = False

        while i < len(line):

            ch = line[i]
            nxt = line[i + 1] if i + 1 < len(line) else ""

            if block_comment:

                if ch == "*" and nxt == "/":
                    block_comment = False
                    i += 2
                else:
                    i += 1

                continue

            if quote:

                if escaped:
                    escaped = False

                elif ch == "\\":
                    escaped = True

                elif ch == quote:
                    quote = None

                i += 1
                continue

            if language in {"C", "C++", "JavaScript", "Java"}:

                if ch == "/" and nxt == "*":
                    block_comment = True
                    i += 2
                    continue

            if ch == "#":
                break

            if language in {"C", "C++", "JavaScript", "Java"}:

                if ch == "/" and nxt == "/":
                    break

            if ch in ("'", '"'):

                quote = ch

            elif ch in PAIRS:

                stack.append((ch, line_no))

            elif ch in REVERSE_PAIRS:

                if not stack:

                    errors.append(
                        make_error(
                            line_no,
                            f"Unexpected symbol '{ch}'",
                            f"The closing '{ch}' does not have an opening symbol.",
                            f"Remove '{ch}' or add the correct opening symbol."
                        )
                    )

                elif stack[-1][0] == REVERSE_PAIRS[ch]:

                    stack.pop()

                else:

                    opening = stack[-1][0]
                    expected = PAIRS[opening]

                    errors.append(
                        make_error(
                            line_no,
                            f"Mismatched symbol '{ch}'",
                            f"The opening '{opening}' does not match this closing symbol.",
                            f"Use '{expected}' to close the opening '{opening}'."
                        )
                    )

                    stack.pop()

            i += 1

        if quote:

            quote_name = "single" if quote == "'" else "double"

            errors.append(
                make_error(
                    line_no,
                    f"Unclosed {quote_name} quote",
                    f"A {quote_name} quote was opened but not closed.",
                    f"Add a closing {quote} quote."
                )
            )

    while stack:

        symbol, line_no = stack.pop()

        errors.append(
            make_error(
                line_no,
                f"Unclosed '{symbol}'",
                f"The opening '{symbol}' does not have a matching closing symbol.",
                f"Add '{PAIRS[symbol]}' at the correct location."
            )
        )

    return errors


# =========================================================
# COMMON SYNTAX
# =========================================================

def check_common_syntax(code, language):

    errors = []

    for i, line in enumerate(code.splitlines(), 1):

        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("//") or stripped.startswith("#"):
            continue

        # PYTHON
        if language == "Python":

            control = re.match(
                r"^(if|elif|for|while|def|class|with|except|async\s+def)\b",
                stripped
            )

            if control or stripped in {
                "else",
                "try",
                "finally"
            }:

                if not stripped.endswith(":"):

                    errors.append(
                        make_error(
                            i,
                            "Missing colon ':'",
                            "This Python statement needs a colon at the end.",
                            "Add ':' at the end of the statement."
                        )
                    )

            if (
                re.match(r"^print\s+.+", stripped)
                and not re.match(r"^print\s*\(", stripped)
            ):

                errors.append(
                    make_error(
                        i,
                        "Invalid print syntax",
                        "Modern Python uses print() as a function.",
                        "Change it to print(...)."
                    )
                )

        # JAVA
        elif language == "Java":

            if re.match(
                r"^(int|long|short|byte)\s+\w+\s*=\s*\d+\.\d+",
                stripped
            ):

                errors.append(
                    make_error(
                        i,
                        "Type mismatch",
                        "An integer variable cannot store a decimal value without conversion.",
                        "Use a whole number or a floating-point type such as double."
                    )
                )

            if re.match(
                r'^int\s+\w+\s*=\s*".*"',
                stripped
            ):

                errors.append(
                    make_error(
                        i,
                        "Type mismatch: cannot assign String to int",
                        "The variable is declared as int but the value is a String.",
                        "Remove the double quotes or use a numeric value."
                    )
                )

            if re.match(
                r'^char\s+\w+\s*=\s*".*"',
                stripped
            ):

                errors.append(
                    make_error(
                        i,
                        "Type mismatch: char cannot use double quotes",
                        "A char uses single quotes and stores one character.",
                        "Use single quotes, for example: 'A'."
                    )
                )

            if re.match(
                r'^String\s+\w+\s*=\s*(\d+(?:\.\d+)?|true|false)\s*;?$',
                stripped
            ):

                errors.append(
                    make_error(
                        i,
                        "Type mismatch: value is not a String",
                        "The assigned value is not written as a String.",
                        'Put the text inside double quotes, for example: "18".'
                    )
                )

        # JAVASCRIPT
        elif language == "JavaScript":

            if re.match(
                r"^(let|const|var)\s+\w+\s*=\s*;",
                stripped
            ):

                errors.append(
                    make_error(
                        i,
                        "Missing value in variable declaration",
                        "The variable declaration has no value after '='.",
                        "Assign a value or remove the '='."
                    )
                )

        # C / C++
        elif language in {"C", "C++"}:

            if re.match(
                r"^(int|float|double|char|long|short|bool|string)\s+\w+\s*=\s*;",
                stripped
            ):

                errors.append(
                    make_error(
                        i,
                        "Missing value in declaration",
                        "The variable declaration has no value after '='.",
                        "Assign a value or remove the '='."
                    )
                )

    return errors


# =========================================================
# SEMICOLON CHECK
# =========================================================

def needs_semicolon(stripped, language):

    if not stripped:
        return False

    if stripped.startswith("//") or stripped.startswith("#"):
        return False

    if stripped.endswith((";", "{", "}", ":")):
        return False

    if language in {"C", "C++"}:

        patterns = [
            r"^(std::)?cout\s*<<",
            r"^cin\s*>>",
            r"^printf\s*\(",
            r"^scanf\s*\(",
            r"^return\b",
            r"^(int|float|double|char|string|long|short|bool)\s+\w+"
        ]

        return any(
            re.search(pattern, stripped)
            for pattern in patterns
        )

    if language == "JavaScript":

        patterns = [
            r"^console\.",
            r"^return\b",
            r"^(let|const|var)\s+",
            r"^document\.",
            r"^alert\s*\("
        ]

        return any(
            re.search(pattern, stripped)
            for pattern in patterns
        )

    if language == "Java":

        patterns = [
            r"^System\.out\.",
            r"^return\b",
            r"^(int|float|double|char|boolean|String|long|short)\s+\w+"
        ]

        return any(
            re.search(pattern, stripped)
            for pattern in patterns
        )

    return False


# =========================================================
# C / C++
# =========================================================

def analyze_c_cpp(code):

    errors = []

    language = "C++" if (
        "cout" in code
        or "#include <iostream>" in code
    ) else "C"

    if not re.search(r"\bmain\s*\(", code):

        errors.append(
            make_error(
                1,
                "Missing main function",
                "A C/C++ program normally needs a main function as its entry point.",
                "Add an int main() function."
            )
        )

    for i, line in enumerate(code.splitlines(), 1):

        stripped = line.strip()

        if needs_semicolon(stripped, language):

            errors.append(
                make_error(
                    i,
                    "Missing semicolon ';'",
                    "This statement should end with a semicolon.",
                    "Add ';' at the end of the statement."
                )
            )

    errors.extend(
        check_common_syntax(code, language)
    )

    errors.extend(
        check_symbols(code, language)
    )

    return errors


# =========================================================
# PYTHON
# =========================================================

def analyze_python(code):

    errors = check_common_syntax(
        code,
        "Python"
    )

    try:

        ast.parse(code)

    except SyntaxError as e:

        message = e.msg or "Invalid Python syntax"
        line = e.lineno or 1

        if not any(
            item["line"] == line
            and message in item["message"]
            for item in errors
        ):

            errors.append(
                make_error(
                    line,
                    f"Python syntax error: {message}",
                    "Python could not parse this code.",
                    "Check the syntax near the reported line."
                )
            )

    errors.extend(
        check_symbols(code, "Python")
    )

    for i, line in enumerate(code.splitlines(), 1):

        if (
            line.strip()
            and line[0] in " \t"
            and i == 1
        ):

            errors.append(
                make_error(
                    i,
                    "Unexpected indentation",
                    "The first Python statement is indented without an enclosing block.",
                    "Remove the extra indentation."
                )
            )

    return errors


# =========================================================
# JAVASCRIPT
# =========================================================

def analyze_javascript(code):

    errors = []

    for i, line in enumerate(code.splitlines(), 1):

        stripped = line.strip()

        if needs_semicolon(
            stripped,
            "JavaScript"
        ):

            errors.append(
                make_error(
                    i,
                    "Missing semicolon ';'",
                    "This JavaScript statement should normally end with a semicolon.",
                    "Add ';' at the end of the statement."
                )
            )

    errors.extend(
        check_common_syntax(code, "JavaScript")
    )

    errors.extend(
        check_symbols(code, "JavaScript")
    )

    return errors


# =========================================================
# JAVA
# =========================================================

def analyze_java(code):

    errors = []

    if not re.search(
        r"\bclass\s+\w+",
        code
    ):

        errors.append(
            make_error(
                1,
                "Missing class",
                "Java code normally needs a class declaration.",
                "Add a class declaration."
            )
        )

    if "public static void main" not in code:

        errors.append(
            make_error(
                1,
                "Missing main method",
                "A standard Java program needs a main method to start execution.",
                "Add public static void main(String[] args)."
            )
        )

    for i, line in enumerate(code.splitlines(), 1):

        stripped = line.strip()

        if needs_semicolon(
            stripped,
            "Java"
        ):

            errors.append(
                make_error(
                    i,
                    "Missing semicolon ';'",
                    "This Java statement should end with a semicolon.",
                    "Add ';' at the end of the statement."
                )
            )

    errors.extend(
        check_common_syntax(code, "Java")
    )

    errors.extend(
        check_symbols(code, "Java")
    )

    return errors


# =========================================================
# REMOVE DUPLICATES
# =========================================================

def remove_duplicates(errors):

    seen = set()
    result = []

    for error in errors:

        key = (
            error["line"],
            error["message"]
        )

        if key not in seen:

            seen.add(key)
            result.append(error)

    return sorted(
        result,
        key=lambda x: (
            x["line"],
            x["message"]
        )
    )


# =========================================================
# QUOTE FIX
# =========================================================

def fix_quotes(lines, language):

    fixed = list(lines)

    for index, line in enumerate(fixed):

        quote = None
        escaped = False
        i = 0

        while i < len(line):

            ch = line[i]

            if quote:

                if escaped:
                    escaped = False

                elif ch == "\\":
                    escaped = True

                elif ch == quote:
                    quote = None

            else:

                if ch == "#":
                    break

                if (
                    language in {"C", "C++", "JavaScript", "Java"}
                    and ch == "/"
                    and i + 1 < len(line)
                    and line[i + 1] == "/"
                ):
                    break

                if ch in ("'", '"'):
                    quote = ch

            i += 1

        if quote is not None:

            fixed[index] = (
                line.rstrip()
                + quote
            )

    return fixed


# =========================================================
# BRACKET FIX
# =========================================================

def fix_symbols(lines, language):

    fixed = list(lines)

    stack = []
    block_comment = False

    for line_index, line in enumerate(fixed):

        chars = list(line)

        quote = None
        escaped = False
        i = 0

        while i < len(chars):

            ch = chars[i]

            nxt = (
                chars[i + 1]
                if i + 1 < len(chars)
                else ""
            )

            if block_comment:

                if ch == "*" and nxt == "/":
                    block_comment = False
                    i += 2
                else:
                    i += 1

                continue

            if quote:

                if escaped:
                    escaped = False

                elif ch == "\\":
                    escaped = True

                elif ch == quote:
                    quote = None

                i += 1
                continue

            if (
                language in {"C", "C++", "JavaScript", "Java"}
                and ch == "/"
                and nxt == "*"
            ):

                block_comment = True
                i += 2
                continue

            if ch == "#":
                break

            if (
                language in {"C", "C++", "JavaScript", "Java"}
                and ch == "/"
                and nxt == "/"
            ):

                break

            if ch in ("'", '"'):

                quote = ch

            elif ch in PAIRS:

                stack.append(ch)

            elif ch in REVERSE_PAIRS:

                if stack:

                    opening = stack[-1]
                    expected = PAIRS[opening]

                    if ch == expected:

                        stack.pop()

                    else:

                        chars[i] = expected
                        stack.pop()

            i += 1

        fixed[line_index] = "".join(chars)

    if stack:

        closers = []

        while stack:

            opening = stack.pop()
            closers.append(PAIRS[opening])

        last_line_index = len(fixed) - 1

        while (
            last_line_index >= 0
            and not fixed[last_line_index].strip()
        ):

            last_line_index -= 1

        if last_line_index >= 0:

            other_closers = [
                x for x in closers
                if x != "}"
            ]

            curly_closers = [
                x for x in closers
                if x == "}"
            ]

            if other_closers:

                fixed[last_line_index] = (
                    fixed[last_line_index].rstrip()
                    + "".join(other_closers)
                )

            for _ in curly_closers:

                fixed.append("}")

        else:

            fixed.extend(closers)

    return fixed


# =========================================================
# JAVA TYPE AUTO FIX
# =========================================================

def fix_java_types(lines):

    fixed = list(lines)

    for index, line in enumerate(fixed):

        # int age = "18";
        pattern = r'^(\s*)int(\s+\w+\s*=\s*)"(-?\d+)"(\s*;?\s*)$'

        match = re.match(pattern, line)

        if match:

            fixed[index] = (
                match.group(1)
                + "int"
                + match.group(2)
                + match.group(3)
                + match.group(4)
            )

            continue

        # char grade = "A";
        pattern = r'^(\s*)char(\s+\w+\s*=\s*)"([A-Za-z])"(\s*;?\s*)$'

        match = re.match(pattern, line)

        if match:

            fixed[index] = (
                match.group(1)
                + "char"
                + match.group(2)
                + "'"
                + match.group(3)
                + "'"
                + match.group(4)
            )

    return fixed


# =========================================================
# COMPLETE AUTO FIX
# =========================================================

def fix_code(code, language):

    lines = code.splitlines()

    fixed_lines = []

    for line in lines:

        stripped = line.strip()

        # PYTHON
        if language == "Python":

            match = re.match(
                r"^(\s*)print\s+(.+)$",
                line
            )

            if (
                match
                and not stripped.startswith("print(")
            ):

                line = (
                    match.group(1)
                    + "print("
                    + match.group(2)
                    + ")"
                )

            stripped_now = line.strip()

            control = re.match(
                r"^(if|elif|for|while|def|class|with|except|async\s+def)\b",
                stripped_now
            )

            if (
                control
                or stripped_now in {
                    "else",
                    "try",
                    "finally"
                }
            ):

                if not stripped_now.endswith(":"):

                    line = (
                        line.rstrip()
                        + ":"
                    )

        # C / C++ / JavaScript / Java
        elif language in {
            "C",
            "C++",
            "JavaScript",
            "Java"
        }:

            if needs_semicolon(
                stripped,
                language
            ):

                line = (
                    line.rstrip()
                    + ";"
                )

        fixed_lines.append(line)

    # Java type fixes
    if language == "Java":

        fixed_lines = fix_java_types(
            fixed_lines
        )

    # Quotes
    fixed_lines = fix_quotes(
        fixed_lines,
        language
    )

    # Brackets
    fixed_lines = fix_symbols(
        fixed_lines,
        language
    )

    return "\n".join(fixed_lines)


# =========================================================
# MAIN ANALYZER
# =========================================================

def analyze_code(code, language):

    if not code.strip():

        return {
            "errors": [
                make_error(
                    1,
                    "No code provided",
                    "The code editor is empty.",
                    "Enter some code and analyze it."
                )
            ],
            "fixed_code": ""
        }

    if language in {"C", "C++"}:

        errors = analyze_c_cpp(code)

    elif language == "Python":

        errors = analyze_python(code)

    elif language == "JavaScript":

        errors = analyze_javascript(code)

    elif language == "Java":

        errors = analyze_java(code)

    else:

        errors = []

    return {
        "errors": remove_duplicates(errors),
        "fixed_code": fix_code(
            code,
            language
        )
    }


# =========================================================
# FLASK
# =========================================================

@app.route("/")
def home():

    return "CodeFix AI Backend is Running!"


@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        code = data.get(
            "code",
            ""
        )

        language = data.get(
            "language",
            "C++"
        )

        result = analyze_code(
            code,
            language
        )

        return jsonify(result)

    except Exception as exc:

        return jsonify(
            {
                "errors": [
                    make_error(
                        1,
                        "Analysis failed",
                        "The analyzer encountered an unexpected problem.",
                        "Check the code and try again."
                    )
                ],
                "fixed_code": "",
                "details": str(exc)
            }
        ), 500


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
