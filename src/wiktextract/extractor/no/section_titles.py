"""Part-of-speech headings used by the Norwegian Wiktionary."""

from ...config import POSSubtitleData

POS_DATA: dict[str, POSSubtitleData] = {
    "Substantiv": {"pos": "noun"},
    "Verb": {"pos": "verb"},
    "Adjektiv": {"pos": "adj"},
    "Adverb": {"pos": "adv"},
    "Egennavn": {"pos": "name"},
    "Pronomen": {"pos": "pron"},
    "Tallord": {"pos": "num"},
    "Preposisjon": {"pos": "prep"},
    "Postposisjon": {"pos": "postp"},
    "Konjunksjon": {"pos": "conj"},
    "Subjunksjon": {"pos": "conj"},
    "Interjeksjon": {"pos": "intj"},
    "Artikkel": {"pos": "article"},
    "Determinativ": {"pos": "det"},
    "Lydord": {"pos": "onomatopoeia"},
    "Forkortelse": {"pos": "abbrev"},
    "Forkortelser": {"pos": "abbrev"},
    "Prefiks": {"pos": "prefix"},
    "Suffiks": {"pos": "suffix"},
    "Symbol": {"pos": "symbol"},
    "Sammentrekning": {"pos": "contraction"},
    "Idiom": {"pos": "phrase"},
    "Uttrykk": {"pos": "phrase"},
    "Ordtak": {"pos": "proverb"},
}
