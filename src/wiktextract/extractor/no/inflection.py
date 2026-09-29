"""Extract Norwegian noun, adjective, and verb forms from grammar tables."""

from wikitextprocessor import NodeKind, WikiNode
from wikitextprocessor.parser import LevelNode

from ...page import clean_node
from ...wxr_context import WiktextractContext
from .models import Form

NOUN_TAGS = (
    ("singular", "indefinite"),
    ("singular", "definite"),
    ("plural", "indefinite"),
    ("plural", "definite"),
)
ADJECTIVE_TAGS = (
    ("masculine", "singular", "indefinite"),
    ("feminine", "singular", "indefinite"),
    ("neuter", "singular", "indefinite"),
    ("plural", "indefinite"),
    ("definite",),
)
ADJECTIVE_GRADE_TAGS = (("positive",), ("comparative",), ("superlative",))
VERB_TAGS = (
    ("infinitive",),
    ("present",),
    ("past",),
    ("past", "participle"),
    ("imperative",),
    ("present", "participle"),
    ("passive",),
)


def row_standards(label: str) -> set[str]:
    label = label.lower()
    standards: set[str] = set()
    if "bokmål" in label:
        standards.add("nb")
    if "nynorsk" in label:
        standards.add("nn")
    if not standards and "norsk" in label:
        standards = {"nb", "nn"}
    return standards


def cell_forms(wxr: WiktextractContext, cell: WikiNode) -> list[str]:
    def usable(form: str) -> bool:
        return bool(form) and not any(char in form for char in "{}[]|")

    links = [
        clean_node(wxr, None, link).strip()
        for link in cell.find_child_recursively(NodeKind.LINK)
    ]
    if links:
        return list(dict.fromkeys(form for form in links if usable(form)))
    text = clean_node(wxr, None, cell.children).strip()
    for prefix in ("ein ", "eit ", "en ", "ei ", "et ", "å ", "har "):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    if not usable(text) or text in {"-", "–", "—", "telles ikke"}:
        return []
    return [text]


def extract_forms(
    wxr: WiktextractContext,
    pos_node: LevelNode,
    pos: str,
    standard: str,
) -> list[Form]:
    if not wxr.config.capture_inflections:
        return []
    tags_by_pos = {
        "noun": NOUN_TAGS,
        "adj": ADJECTIVE_TAGS,
        "verb": VERB_TAGS,
    }
    column_tags = tags_by_pos.get(pos)
    if column_tags is None:
        return []

    forms: list[Form] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for section in pos_node.find_child(NodeKind.LEVEL4):
        if clean_node(wxr, None, section.largs).strip() != "Grammatikk":
            continue
        raw = wxr.wtp.node_to_wikitext(section.children)
        expanded = wxr.wtp.parse(raw, expand_all=True)
        for table in expanded.find_child_recursively(NodeKind.TABLE):
            for row in table.find_child(NodeKind.TABLE_ROW):
                cells = list(row.find_child(NodeKind.TABLE_CELL))
                row_tags = column_tags
                if pos == "adj" and len(cells) == 4:
                    row_tags = ADJECTIVE_GRADE_TAGS
                required = 2 if pos == "verb" else len(row_tags) + 1
                if len(cells) < required:
                    continue
                label = clean_node(wxr, None, cells[-1].children)
                if standard not in row_standards(label):
                    continue
                for cell, tags in zip(cells[:-1], row_tags):
                    for form in cell_forms(wxr, cell):
                        key = (form, tags)
                        if key not in seen:
                            seen.add(key)
                            forms.append(Form(form=form, tags=list(tags)))
    return forms
