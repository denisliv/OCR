import re


def fix_ocr_markdown(md: str) -> str:
    lines = md.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped[1:-1].split("|")]
            if all(cell == "" for cell in cells):
                continue
        cleaned.append(line)
    while cleaned and cleaned[-1].strip() == "":
        cleaned.pop()
    return "\n".join(cleaned)


def remove_parentheses_around_numbers(text: str) -> str:
    if not isinstance(text, str):
        return text

    def replace_match(m):
        inner = m.group(1)
        if re.fullmatch(r"[\d\s]+", inner.strip()):
            return inner.replace(" ", "")
        return m.group(0)

    return re.sub(r"\(([^)]+)\)", replace_match, text)
