"""Text normalisation for French / Arabic / English goods descriptions."""
import re
import unicodedata

_AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"})
_AR_DIACRITICS = re.compile(r"[ً-ْـ]")
_STOP = {"de", "du", "des", "la", "le", "les", "en", "et", "pour", "a", "au", "aux", "un", "une",
         "the", "of", "for", "and", "من", "في", "على", "و", "ال", "مع", "ل"}


def normalize(text: str) -> str:
    text = _AR_DIACRITICS.sub("", text.lower()).translate(_AR_MAP)
    # strip Latin accents but keep Arabic letters intact
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.category(ch) == "Mn":
            continue
        out.append(ch)
    return "".join(out)


def tokens(text: str) -> set[str]:
    words = re.findall(r"[\w]+", normalize(text))
    result = set()
    for w in words:
        if w in _STOP or len(w) < 2:
            continue
        # Arabic definite article: "الحديد" -> "حديد"
        if w.startswith("ال") and len(w) > 4:
            w = w[2:]
        # naive French/English plural
        if w.isascii() and len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        result.add(w)
    return result
