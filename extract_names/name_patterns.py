"""Patterns for compound labels, compound names and the data blocks around them in SI text.
Used by extract_names.py and compound_names.py."""

import re


# ===== Labels =====

# One compound label: 3a, 12, 5', S-2, SI-3, Boc-4, 3.12, 3ab, 4aB, (R)-7b
LAB = (r"(?:\([^()\s]{1,12}\)-)?"                 # optional stereo prefix: "(R)-", "(rac)-"
       r"(?:[A-Z]{1,2}-?|[A-Z][A-Za-z]{1,4}-)?"   # optional letter prefix: "S", "SI-", "Boc-"
       r"\d{1,3}"                                 # number
       r"(?:\.\d{1,3}(?![\d.]))?"                 # optional decimal part: "3.12" (not a shift "3.125")
       r"[′'’]?"                                  # optional prime
       r"(?:[a-z]{1,2}[A-Z]?|[a-z]{0,3})"         # optional letters: "a", "ab", "aB"
       r"[′'’]?"                                  # optional prime after the letters
       r"(?:-[a-z](?![A-Za-z]))?")                # v2: optional "-a" of an intermediate: "1s-a", "1p-c"
# Words of a physical description ("white solid", "colourless oil") that follow a label
STATE = (r"(?:white|colou?rless|yellow|pale|light|brown|orange|red|green|blue|purple|pink|black|grey|gray"
         r"|beige|off-white|tan|amorphous|viscous|clear|dark|solid|oil|liquid|foam|gum|syrup|wax|crystal)")

# "(3a)", "(3a-major)"
LABEL_PAREN = re.compile(r"\(\s*(" + LAB + r")\s*(?:[–-]\s?(?:major|minor))?\s*\)")
# "3a. Name. White solid": a label at the start of the text or of a sentence, then ". "
LABEL_DOT = re.compile(r"(?:^\s*|(?<=\.\s))(" + LAB + r")\.\s(?=[A-Za-z\(\[\d])")
# "Product 4e: name ...", "Compound 12: name ..."
# v2.1: also with a short alias before the colon: "Compound 8 (Db1):"
LABEL_CPD = re.compile(r"\b(?:Compound|Product)\s+(" + LAB + r")(?:\s?\([^()]{1,15}\))?\s?:\s", re.I)
# "Name 3a: white solid", "Name 3a, colourless oil"
LABEL_COLON = re.compile(r"(?<=\s)(" + LAB + r")\s?(?::\s(?=[A-Za-z\(\[])|,\s(?=" + STATE + r"))", re.I)
# "Name 25 The compound was obtained ...": a bare label between a name and the procedure
LABEL_BARE = re.compile(
    r"(?<=[a-z\)\]]\s)(" + LAB + r")\s"
    r"(?=(?:The|This|was|Following|According|Prepared|Synthesi[sz]ed|Obtained|Yield|Using)\b|" + STATE + r"\b)")
# "... afforded 3h as a white solid", "gave the product (4b) in 85% yield": group 1 = label
AFFORD_LABEL = re.compile(
    r"\b(?:afford(?:ed|s)?|gave|give|giving|obtain(?:ed)?|yield(?:ed|ing)?|furnish(?:ed)?|provid(?:ed|e))"
    r"\s+(?:\w+\s+){0,4}?"                        # up to four words: "the desired product"
    r"\(?(" + LAB + r")\)?\s*(?:as|\(|was|in)\b", re.I)


# v2: a number after these words is not a compound label: "Trial 1:", "STEP 2:", "Entry 3,", "Table 1:"
NOT_LABEL_BEFORE = re.compile(
    r"\b(?:trials?|steps?|entry|entries|runs?|tables?|fig(?:ure)?s?|schemes?|methods?|procedures?|routes?"
    r"|conditions?|eq(?:uation)?s?|batch|experiments?|examples?|parts?|sections?|stages?|cycles?|attempts?)"
    r"\.?\s*$", re.I)
# v2: a compound described only by a reference ends its entry: "Characterization data matches literature
# precedent.", "Spectral data are in agreement with those reported." - labels before it are not used
DATA_BY_REFERENCE = re.compile(
    r"\bdata\s+(?:(?:is|are|was|were)\s+)?(?:match(?:es|ed)?|in\s+(?:good\s+)?agreement|consistent)\b"
    r"[^.]{0,120}\.(?:\s*(?:\[[^\]]{1,20}\]|\^\{[^}]{1,20}\}))?\s*\)?", re.I)


# v2: "4a-h", "1a-l": a range of compounds, not a label ("1s-a", "7-a" are labels of intermediates)
def is_label_range(label):
    m = re.search(r"\d([a-z])-([a-z])$", label)
    return bool(m) and m.group(2) > m.group(1)


# ===== Data blocks =====

# 19F / 31P descriptions that follow the 1H description (needed for heteronuclear couplings):
# from the header up to the next NMR header, HRMS, IR or the end of the text (at most 800 characters)
HETERO_DESC = re.compile(
    r"(?<![0-9A-Za-z])(?:19\s?F|31\s?P)\s?(?:\{[^}]*\})?\s?-?\s?NMR.{0,800}?"
    r"(?=(?<![0-9A-Za-z])(?:1[13]\s?C|19\s?F|31\s?P|11\s?B|29\s?Si)\s?(?:\{[^}]*\})?\s?-?\s?NMR|HRMS|HR-?MS|\bIR\b|$)",
    re.S)
# Elemental analysis "Calcd for C13H13BrF6 (362.01):" - the molar mass in brackets is not a label
CALCD_MASS = re.compile(r"\b(?:Anal\.?\s*)?[Cc]alc(?:d|\.|ulated)\.?\s*(?:for)?\s*:?\s*\(?[A-Z][A-Za-z0-9·]{1,40}\)?\s*$")
# HRMS "found 312.1234": the end of the previous compound's data
FOUND = re.compile(r"\b[Ff]ound\b\s*:?\s*\d{2,4}\.\d{3,5}")
# A section heading at the start of a name: "2.3 ", "S4. ", "IV. ", or "... 3.1 Synthesis"
HEADING = re.compile(r"^(?:[A-Z]?\d+(?:\.\d+)*\.?\s|[IVX]+\.\s)|\s\d+\.\d+\.?\s[A-Z]")


# ===== Names =====

# Text that cannot be a compound name: amounts, yields, NMR words, verbs of a procedure
NOT_NAME = re.compile(r"%|=|\bmg\b|mmol|\bequiv|\bNMR\b|\bHRMS\b"
                      r"|\b(?:data|procedure|solution|mixture|was|were|added|afforded|gave)\b", re.I)
# A name contains at least one word ending typical of chemical names
NAME_LIKE = re.compile(r"(?:yl|ane|ene|yne|one|ol|al|ide|ate|ite|ine|ole|oic|ium|ane|an|ose|oside|ile|amide"
                       r"|imine|azole|borane|borate)\b", re.I)
# Words before a name that are not part of it
NAME_JUNK = re.compile(r"^(?:Synthesis|Preparation) of\s+|^Compound\s+", re.I)
# Text that is not part of a name; a name candidate is cut after the last of these:
JUNK_CUT = re.compile(
    r"chromatogram\b"
    r"|^SI?-?\d+\s+(?=\S)"                        # SI page number at the start: "S12 "
    r"|Spectr(?:um|a)\s+of\s+\S+\s*(?:\([^()]*\))?"  # "Spectrum of 3a (CDCl3)"
    r"|\b\d+\s*/\s*\d+\s+(?=\S)"                  # page counter "12 / 80"
    r"|Supporting Information(?:\s*S-?\d+)?"
    r"|\bCharacteri[sz]ations?\s+of\s+\S+(?:\s*[、,]\s*\S+)*"   # "Characterization of 3a, 3b"
    r"|\b(?:Synthesis|Preparation)\s+of\s+(?=\S)"
    r"|^(?:Compound|Product|Entry)\b\s*"
    r"|\bcarbons?\s+(?=[A-Z(\d])", re.I)            # v2: end of a 13C assignment: "Methoxy carbon Tert-butyl ..."
# A run of short tokens at the start = atom labels of a structure drawing (e.g. "N H O Se Ph O2N")
DRAWING = re.compile(r"^(?:(?:[A-Za-z]{1,4}\d{0,3}[+\-−]?|[\d.,%]+)\s+){2,}(?=\S)")
# Where an entry ends: sentence end, "; ", ": " or a bullet (names contain none of these)
SEG = re.compile(r"\.(?:\^\{[^}]*\})?\s+(?=\S)|;\s|:\s|\)\s*:\s|•")
# Words that start the procedure or the data after a name
AFTER_NAME = re.compile(
    r"\s(?:According|Following|Prepared|Synthesi[sz]ed|Obtained|Using|Under|To\s+a"
    r"|The\s+(?:title\s+)?(?:compound|product|reaction)"
    r"|General|Yield|Purification|Purified|Starting|From|Isolated|Compound\s+\S+\s+was)\b"
    r"|\s" + STATE + r"\b", re.I)
# Ordinary prose words (a heading such as "Study on byproducts" before a name)
PROSE = re.compile(r"^(?:[A-Za-z&]+|[A-Z][a-z]*(?:-[A-Z][a-z]+)+|\([A-Z]{1,4}\)|\d+(?:\.\d+)+\.?)$")
# Words that look like prose but are part of a name ("methyl", "sodium", "...ate")
CHEM_WORD = re.compile(
    r"^(?:(?:di|tri|tetra)?(?:methyl|ethyl|propyl|butyl|pentyl|hexyl|benzyl|phenyl|allyl|vinyl|isopropyl"
    r"|isobutyl|cyclohexyl|tert|sec|neo)"
    r"|sodium|potassium|lithium|cesium|caesium|ammonium|.{3,}(?:yl|ate|ide|ine|ane|ene|one|ol|ium|ose|oside|ile))$",
    re.I)
# How a systematic name can start: a bracket, a locant, ± or a stereo prefix
NAME_START = re.compile(r"^(?:[\(\[\d±]|(?:rac|meso|cis|trans|endo|exo|syn|anti)-)")
# Words of prose that never occur in a compound name
PROSE_IN_NAME = re.compile(
    r"\b(?:the|with|from|those|should|be|been|this|that|these|reported|literature|eluent|mesh|flow|obtaining"
    r"|pure|followed|handling|protocols?|degassed|optical|rotation|spectrum|spectra|figure|table|scheme"
    r"|chromatogram)\b", re.I)
