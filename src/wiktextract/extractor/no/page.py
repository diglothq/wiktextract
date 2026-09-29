"""Extract entries from the Norwegian Wiktionary, including Bokmål and Nynorsk.

The edition uses one ``Norsk`` language section for both written standards.
Headword templates and per-sense norm parameters decide which standard receives
an entry. Unmarked Norwegian senses are emitted only when a headword template
establishes the standard, so a Nynorsk-only page cannot silently become Bokmål.
"""

import re
from typing import Any

from mediawiki_langcodes import code_to_name, name_to_code
from wikitextprocessor import NodeKind, TemplateNode, WikiNode
from wikitextprocessor.parser import LEVEL_KIND_FLAGS, LevelNode

from ...page import clean_node
from ...wxr_context import WiktextractContext
from .inflection import extract_forms
from .models import FormOf, Sense, Translation, WordEntry
from .section_titles import POS_DATA

YES = {"ja", "yes", "1", "true"}
NO = {"nei", "no", "0", "false"}
FORM_OF_SUFFIX = "-bøyningsform"
TRANSLATION_TEMPLATES = {"overs", "o"}


def template_arg(
    wxr: WiktextractContext, node: TemplateNode, key: int | str
) -> str:
    value = node.template_parameters.get(key, "")
    return clean_node(wxr, None, value).strip()


def written_standards(
    wxr: WiktextractContext, node: TemplateNode
) -> set[str] | None:
    """Return explicit written-standard evidence from a template."""
    name = node.template_name.strip().lower()
    if name.startswith("nb-"):
        standards = {"nb"}
    elif name.startswith("nn-"):
        standards = {"nn"}
    elif name.startswith("no-") or name == "norm":
        standards = {"nb", "nn"}
    elif name == "infl":
        language = template_arg(wxr, node, 1).lower()
        if language == "nb":
            standards = {"nb"}
        elif language == "nn":
            standards = {"nn"}
        elif language == "no":
            standards = {"nb", "nn"}
        else:
            return None
    else:
        return None

    markers = {
        code: template_arg(wxr, node, code).lower() for code in ("nb", "nn")
    }
    if any(marker in YES for marker in markers.values()):
        standards = set()
    for code in ("nb", "nn"):
        marker = markers[code]
        if marker in YES:
            standards.add(code)
        elif marker in NO:
            standards.discard(code)
    return standards


def headword_standards(wxr: WiktextractContext, node: LevelNode) -> set[str]:
    standards: set[str] = set()
    norm_standards: set[str] | None = None
    for template in node.find_child(NodeKind.TEMPLATE):
        assert isinstance(template, TemplateNode)
        name = template.template_name.strip().lower()
        if name in {"norm", "infl"} or (
            name.startswith(("no-", "nb-", "nn-"))
            and FORM_OF_SUFFIX not in name
            and not name.endswith(("-start", "-slutt", "-topp", "-bunn"))
        ):
            found = written_standards(wxr, template)
            if found is not None:
                if name == "norm":
                    if norm_standards is None:
                        norm_standards = found
                    else:
                        norm_standards &= found
                else:
                    standards.update(found)
    if norm_standards is not None:
        return standards & norm_standards if standards else norm_standards
    return standards


def gloss_senses(
    wxr: WiktextractContext, pos_node: LevelNode, head_standards: set[str]
) -> dict[str, list[Sense]]:
    result: dict[str, list[Sense]] = {
        standard: [] for standard in sorted(head_standards | {"nb", "nn"})
    }
    for list_node in pos_node.find_child(NodeKind.LIST):
        if list_node.sarg != "#":
            continue
        for item in list_node.find_child(NodeKind.LIST_ITEM):
            assert isinstance(item, WikiNode)
            nodes = [
                child
                for child in item.children
                if not (
                    isinstance(child, WikiNode) and child.kind == NodeKind.LIST
                )
            ]
            standards: set[str] | None = None
            form_of: list[FormOf] = []
            for child in item.find_child_recursively(NodeKind.TEMPLATE):
                assert isinstance(child, TemplateNode)
                name = child.template_name.strip().lower()
                if name.endswith(FORM_OF_SUFFIX) or name == "norm":
                    found = written_standards(wxr, child)
                    if found is not None:
                        standards = (
                            found if standards is None else standards & found
                        )
                if name.endswith(FORM_OF_SUFFIX):
                    lemma = template_arg(wxr, child, 2)
                    if lemma:
                        form_of.append(FormOf(word=lemma))
            if standards is None:
                standards = head_standards
            elif head_standards:
                standards &= head_standards

            gloss = clean_node(wxr, None, nodes).strip()
            sense = Sense()
            if gloss:
                sense.glosses.append(gloss)
            if form_of:
                sense.form_of = form_of
                sense.tags.append("form-of")
            if not sense.glosses and not sense.form_of:
                continue
            for standard in standards:
                result[standard].append(sense.model_copy(deep=True))
    return result


def extract_translations(
    wxr: WiktextractContext, pos_node: LevelNode
) -> list[Translation]:
    translations: list[Translation] = []
    seen: set[tuple[str, str, str]] = set()
    for section in pos_node.find_child(LEVEL_KIND_FLAGS):
        if clean_node(wxr, None, section.largs).strip() != "Oversettelser":
            continue
        sense = ""
        for node in section.find_child_recursively(NodeKind.TEMPLATE):
            assert isinstance(node, TemplateNode)
            name = node.template_name.strip().lower()
            if name == "overs-topp":
                sense = template_arg(wxr, node, 1)
            elif name in TRANSLATION_TEMPLATES:
                lang_code = template_arg(wxr, node, 1)
                word = template_arg(wxr, node, 2)
                identity = (lang_code, word, sense)
                if lang_code and word and identity not in seen:
                    seen.add(identity)
                    translations.append(
                        Translation(
                            lang_code=lang_code,
                            lang=code_to_name(lang_code, "no") or "",
                            word=word,
                            sense=sense,
                        )
                    )
    return translations


def parse_pos(
    wxr: WiktextractContext,
    page_title: str,
    lang_code: str,
    lang_name: str,
    pos_node: LevelNode,
    pos_title: str,
) -> list[WordEntry]:
    pos = POS_DATA[pos_title]["pos"]
    if lang_code == "no":
        head_standards = headword_standards(wxr, pos_node)
        senses_by_standard = gloss_senses(wxr, pos_node, head_standards)
        translations = extract_translations(wxr, pos_node)
        return [
            WordEntry(
                word=page_title,
                lang_code=standard,
                lang="Norsk bokmål" if standard == "nb" else "Norsk nynorsk",
                pos=pos,
                pos_title=pos_title,
                senses=senses,
                forms=extract_forms(wxr, pos_node, pos, standard),
                translations=[tr.model_copy(deep=True) for tr in translations],
            )
            for standard, senses in senses_by_standard.items()
            if senses
            and (
                wxr.config.capture_language_codes is None
                or standard in wxr.config.capture_language_codes
            )
        ]

    senses_by_standard = gloss_senses(wxr, pos_node, {lang_code})
    senses = senses_by_standard.get(lang_code, [])
    if not senses:
        return []
    return [
        WordEntry(
            word=page_title,
            lang_code=lang_code,
            lang=lang_name,
            pos=pos,
            pos_title=pos_title,
            senses=senses,
        )
    ]


def parse_page(
    wxr: WiktextractContext, page_title: str, page_text: str
) -> list[dict[str, Any]]:
    wxr.wtp.start_page(page_title)
    tree = wxr.wtp.parse(page_text, pre_expand=True)
    page_data: list[WordEntry] = []
    for language_node in tree.find_child(NodeKind.LEVEL2):
        lang_name = clean_node(wxr, None, language_node.largs).strip()
        lang_code = (
            "no" if lang_name == "Norsk" else name_to_code(lang_name, "no")
        )
        if not lang_code:
            continue
        if (
            lang_code != "no"
            and wxr.config.capture_language_codes is not None
            and lang_code not in wxr.config.capture_language_codes
        ):
            continue
        wxr.wtp.start_section(lang_name)
        for pos_node in language_node.find_child(NodeKind.LEVEL3):
            title = clean_node(wxr, None, pos_node.largs).strip()
            pos_title = re.sub(r"\s+\d+$", "", title)
            if pos_title not in POS_DATA:
                continue
            wxr.wtp.start_subsection(title)
            page_data.extend(
                parse_pos(
                    wxr, page_title, lang_code, lang_name, pos_node, pos_title
                )
            )
    return [entry.model_dump(exclude_defaults=True) for entry in page_data]
