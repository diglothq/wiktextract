"""Representative Norwegian Wiktionary written-standard extraction cases."""

from unittest import TestCase

from wikitextprocessor import Wtp

from wiktextract.config import WiktionaryConfig
from wiktextract.extractor.no.page import parse_page
from wiktextract.wxr_context import WiktextractContext


class TestNoExtract(TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.wxr = WiktextractContext(
            Wtp(lang_code="no"),
            WiktionaryConfig(dump_file_lang_code="no", capture_language_codes=None),
        )

    def tearDown(self) -> None:
        self.wxr.wtp.close_db_conn()

    def test_shared_entry_and_french_translation(self) -> None:
        entries = parse_page(
            self.wxr,
            "ordbok",
            """==Norsk==
===Substantiv===
{{no-sub|f}}
# En bok med en liste over ord.
====Oversettelser====
{{overs-topp|Bok med liste over ord}}
* {{overs|fr|dictionnaire|m}}
{{overs-bunn}}
""",
        )
        self.assertEqual({entry["lang_code"] for entry in entries}, {"nb", "nn"})
        self.assertEqual(entries[0]["pos"], "noun")
        self.assertEqual(entries[0]["senses"][0]["glosses"], ["En bok med en liste over ord."])
        self.assertIn(
            {"lang_code": "fr", "lang": "fransk", "word": "dictionnaire", "sense": "Bok med liste over ord"},
            entries[0]["translations"],
        )

    def test_bokmal_only_and_nynorsk_only_sections(self) -> None:
        bokmal = parse_page(
            self.wxr,
            "være",
            "==Norsk==\n===Verb===\n{{nb-verb}}\n# eksistere\n",
        )
        nynorsk = parse_page(
            self.wxr,
            "vere",
            "==Norsk==\n===Verb===\n{{nn-verb}}\n# eksistere\n",
        )
        self.assertEqual([entry["lang_code"] for entry in bokmal], ["nb"])
        self.assertEqual([entry["lang_code"] for entry in nynorsk], ["nn"])

    def test_mixed_pos_keeps_only_bokmal_adjective(self) -> None:
        entries = parse_page(
            self.wxr,
            "ven",
            """==Norsk==
===Substantiv===
{{nn-sub|m}}
# person man kjenner godt
===Adjektiv===
{{no-adj}}
# vakker
""",
        )
        self.assertEqual(
            [(entry["lang_code"], entry["pos"]) for entry in entries],
            [("nn", "noun"), ("nb", "adj"), ("nn", "adj")],
        )

    def test_form_of_standards_are_sense_specific(self) -> None:
        entries = parse_page(
            self.wxr,
            "bøker",
            """==Norsk==
===Substantiv===
#{{no-sub-bøyningsform|uf|bok|nb=ja|nn=ja}}
#{{no-sub-bøyningsform|uf|bøk|nb=ja|nn=nei}}
""",
        )
        nb = next(entry for entry in entries if entry["lang_code"] == "nb")
        nn = next(entry for entry in entries if entry["lang_code"] == "nn")
        self.assertEqual(
            [sense["form_of"][0]["word"] for sense in nb["senses"]],
            ["bok", "bøk"],
        )
        self.assertEqual(
            [sense["form_of"][0]["word"] for sense in nn["senses"]],
            ["bok"],
        )

    def test_norm_template_restricts_a_shared_headword_sense(self) -> None:
        entries = parse_page(
            self.wxr,
            "døme",
            """==Norsk==
===Substantiv===
{{no-sub|n}}
# {{norm|nn=ja}} nynorsk-only meaning
# {{norm|nb=ja}} bokmål-only meaning
""",
        )
        nb = next(entry for entry in entries if entry["lang_code"] == "nb")
        nn = next(entry for entry in entries if entry["lang_code"] == "nn")
        self.assertEqual(len(nb["senses"]), 1)
        self.assertEqual(len(nn["senses"]), 1)

    def test_unmarked_norwegian_entry_is_not_assigned_to_bokmal(self) -> None:
        entries = parse_page(self.wxr, "ukjent", "==Norsk==\n===Verb===\n# ord\n")
        self.assertEqual(entries, [])

    def test_language_filter_excludes_nynorsk_and_other_languages(self) -> None:
        self.wxr.config.capture_language_codes = {"nb"}
        entries = parse_page(
            self.wxr,
            "hus",
            """==Norsk==
===Substantiv===
{{no-sub|n}}
# bygning
==Dansk==
===Substantiv===
# hus
""",
        )
        self.assertEqual([entry["lang_code"] for entry in entries], ["nb"])

    def test_other_language_section_with_all_languages_enabled(self) -> None:
        entries = parse_page(
            self.wxr,
            "maison",
            "==Fransk==\n===Substantiv===\n# hus\n",
        )
        self.assertEqual([entry["lang_code"] for entry in entries], ["fr"])

    def test_legacy_infl_headword_template(self) -> None:
        entries = parse_page(
            self.wxr,
            "ei",
            "==Norsk==\n===Artikkel===\n{{infl|no|artikkel}}\n# hunkjønnsartikkel\n",
        )
        self.assertEqual([entry["lang_code"] for entry in entries], ["nb", "nn"])

    def test_translation_template_parameters_are_not_extra_words(self) -> None:
        entries = parse_page(
            self.wxr,
            "hus",
            """==Norsk==
===Substantiv===
{{no-sub|n}}
# bygning
====Oversettelser====
{{overs-topp|bygning}}
* {{overs|fr|maison|f|p}}, {{o|fr|demeure|f}}
{{overs-bunn}}
""",
        )
        self.assertEqual(
            [item["word"] for item in entries[0]["translations"]],
            ["maison", "demeure"],
        )

    def test_noun_table_forms_keep_bokmal_row(self) -> None:
        self.wxr.wtp.add_page(
            "Mal:no-sub-n1",
            10,
            """{| class="grammar"
|-
|[[hus]]||[[huset]]||[[hus]]||[[husene]]||(bokmål)
|-
|[[hus]]||[[huset]]||[[hus]]||[[husa]]||(nynorsk)
|}
""",
        )
        entries = parse_page(
            self.wxr,
            "hus",
            """==Norsk==
===Substantiv===
{{no-sub|n}}
# bygning
====Grammatikk====
{{no-sub-n1}}
""",
        )
        nb = next(entry for entry in entries if entry["lang_code"] == "nb")
        nn = next(entry for entry in entries if entry["lang_code"] == "nn")
        self.assertIn({"form": "husene", "tags": ["plural", "definite"]}, nb["forms"])
        self.assertNotIn(
            {"form": "husa", "tags": ["plural", "definite"]}, nb["forms"]
        )
        self.assertIn({"form": "husa", "tags": ["plural", "definite"]}, nn["forms"])

    def test_verb_table_with_omitted_passive_column(self) -> None:
        self.wxr.wtp.add_page(
            "Mal:verb-bøyning",
            10,
            """{| class="grammar"
|-
|å [[være]]||[[er]]||[[var]]||har [[vært]]||[[vær]]||[[værende]]||(bokmål)
|}
""",
        )
        entries = parse_page(
            self.wxr,
            "være",
            """==Norsk==
===Verb===
{{nb-verb}}
# eksistere
====Grammatikk====
{{verb-bøyning}}
""",
        )
        forms = entries[0]["forms"]
        self.assertIn({"form": "er", "tags": ["present"]}, forms)
        self.assertIn({"form": "vært", "tags": ["past", "participle"]}, forms)

    def test_nested_adjective_tables_include_comparison(self) -> None:
        self.wxr.wtp.add_page(
            "Mal:adjektiv-bøyning",
            10,
            """{|
|-
|
{| class="grammar"
|-
|[[stor]]||[[stor]]||[[stort]]||[[store]]||[[store]]||(bokmål/nynorsk)
|}
|
{| class="grammar"
|-
|[[stor]]||[[større]]||[[størst]]||(bokmål/nynorsk)
|}
|}
""",
        )
        entries = parse_page(
            self.wxr,
            "stor",
            """==Norsk==
===Adjektiv===
{{no-adj}}
# av stor størrelse
====Grammatikk====
{{adjektiv-bøyning}}
""",
        )
        forms = entries[0]["forms"]
        self.assertIn({"form": "stort", "tags": ["neuter", "singular", "indefinite"]}, forms)
        self.assertIn({"form": "større", "tags": ["comparative"]}, forms)

    def test_unexpanded_template_placeholders_are_not_forms(self) -> None:
        self.wxr.wtp.add_page(
            "Mal:broken-forms",
            10,
            """{| class="grammar"
|-
|[[hus]]||[[huset]]||{{{5}}}||[[{{{6}}}]]||(bokmål)
|}
""",
        )
        entries = parse_page(
            self.wxr,
            "hus",
            """==Norsk==
===Substantiv===
{{nb-sub}}
# bygning
====Grammatikk====
{{broken-forms}}
""",
        )
        self.assertEqual(
            [form["form"] for form in entries[0]["forms"]], ["hus", "huset"]
        )
