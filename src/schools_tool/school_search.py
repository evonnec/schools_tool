"""Part 2: find schools by name, city, and state from a plain-text query.

Ranking rules, in order:

1. Each query word scores the schools it matches. A word matches a school
   when it equals a word in the school's name, city, or state (name or postal
   code); for slightly less when it is the abbreviation or expansion of one
   ("elementary" finds ELEM); and for partial credit when it starts a longer
   word ("highl" finds HIGHLAND). A word that matches nothing that way may
   match a word one typo away ("kuskokwin" finds KUSKOKWIM) for less.
2. Rare words count for more than common ones, so "foley" decides more than
   "high", and "school", which most names contain, barely counts.
3. Ties go to the school whose name is closest to the query (most words in
   common, fewest words not in common), then whose city is, then to shorter
   names, then alphabetically. HIGHLAND PARK ELEMENTARY SCHOOL comes before
   an elementary school that is only located in Highland Park, and RANCHO
   CUCAMONGA MIDDLE before CUCAMONGA MIDDLE in Rancho Cucamonga.
4. Results with the same name, city, and state are shown once.
"""

import time

from schools_tool.dataset import School, load_schools, load_state_names

RESULT_LIMIT = 3

# Points for each kind of match, multiplied by how rare the query word is.
EXACT = 10
ABBREVIATION = 9
PREFIX = 6
TYPO = 5

# Words shorter than these are matched exactly only; "in" should not match
# every word that starts with "in".
MIN_PREFIX_LENGTH = 3
MIN_TYPO_LENGTH = 4

# Abbreviations common in school names (2,229 names say ELEM). A query word
# matches both the word as written and its abbreviation or expansion, so
# "elementary" finds ELEM and "elem" finds ELEMENTARY.
ABBREVIATIONS = {
    "ACAD": ("ACADEMY",),
    "CTR": ("CENTER",),
    "ELEM": ("ELEMENTARY",),
    "FT": ("FORT",),
    "HS": ("HIGH", "SCHOOL"),
    "HTS": ("HEIGHTS",),
    "JR": ("JUNIOR",),
    "MID": ("MIDDLE",),
    "MT": ("MOUNT",),
    "SCH": ("SCHOOL",),
    "SCHL": ("SCHOOL",),
    "SR": ("SENIOR",),
}

TYPO_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def abbreviation_equivalents() -> dict[str, list[str]]:
    """Map each abbreviation to its words and each word to its abbreviations."""
    equivalents: dict[str, list[str]] = {}
    for abbreviation, words in ABBREVIATIONS.items():
        for word in words:
            equivalents.setdefault(abbreviation, []).append(word)
            equivalents.setdefault(word, []).append(abbreviation)
    return equivalents


EQUIVALENTS = abbreviation_equivalents()


def tokenize(text: str) -> list[str]:
    """Split text into upper-case words of letters and digits.

    Apostrophes are dropped ("MARY'S" -> "MARYS") and other punctuation
    separates words ("COLLINS-RIVERSIDE" -> "COLLINS", "RIVERSIDE").
    """
    without_apostrophes = text.upper().replace("'", "").replace("’", "")
    spaced = "".join(char if char.isalnum() else " " for char in without_apostrophes)
    return spaced.split()


def one_edit_away(word: str) -> set[str]:
    """Every string one deletion, swap, replacement, or insertion from word."""
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [left + right[1:] for left, right in splits if right]
    swaps = [
        left + right[1] + right[0] + right[2:]
        for left, right in splits
        if len(right) > 1
    ]
    replaces = [
        left + char + right[1:]
        for left, right in splits
        if right
        for char in TYPO_ALPHABET
    ]
    inserts = [left + char + right for left, right in splits for char in TYPO_ALPHABET]
    return set(deletes + swaps + replaces + inserts) - {word}


class SchoolIndex:
    """An inverted index over schools, built once so each search is fast."""

    def __init__(self, schools: list[School], state_names: dict[str, str]) -> None:
        self.schools = schools
        self._name_tokens = [set(tokenize(school.name)) for school in schools]
        self._city_tokens = [set(tokenize(school.city)) for school in schools]

        # token -> positions in self.schools of the schools containing it
        self._postings: dict[str, list[int]] = {}
        for position, school in enumerate(schools):
            searchable = f"{school.name} {school.city} {state_names.get(school.state, '')} {school.state}"
            for token in set(tokenize(searchable)):
                self._postings.setdefault(token, []).append(position)

        # prefix -> longer tokens that start with it
        self._completions: dict[str, list[str]] = {}
        for token in self._postings:
            for end in range(MIN_PREFIX_LENGTH, len(token)):
                self._completions.setdefault(token[:end], []).append(token)

    def search(self, query: str, limit: int = RESULT_LIMIT) -> list[School]:
        if limit < 1:
            return []
        scores: dict[int, int] = {}
        # For each query word, the indexed tokens it matches and how well
        word_matches: list[dict[str, int]] = []
        for word in dict.fromkeys(tokenize(query)):
            matches = self._matching_tokens(word)
            word_matches.append(matches)

            quality_by_position: dict[int, int] = {}
            for token, quality in matches.items():
                for position in self._postings[token]:
                    if quality_by_position.get(position, 0) < quality:
                        quality_by_position[position] = quality
            weight = self._rarity(len(quality_by_position))
            for position, quality in quality_by_position.items():
                scores[position] = scores.get(position, 0) + quality * weight
        return self._rank(scores, word_matches, limit)

    def _matching_tokens(self, word: str) -> dict[str, int]:
        """The indexed tokens a query word matches, with the best quality of each."""
        candidates = []
        if word in self._postings:
            candidates.append((word, EXACT))
        candidates.extend(
            (token, ABBREVIATION)
            for token in EQUIVALENTS.get(word, [])
            if token in self._postings
        )
        if len(word) >= MIN_PREFIX_LENGTH:
            candidates.extend(
                (token, PREFIX) for token in self._completions.get(word, [])
            )
        if not candidates and len(word) >= MIN_TYPO_LENGTH:
            candidates.extend(
                (token, TYPO)
                for token in one_edit_away(word)
                if token in self._postings
            )

        matches: dict[str, int] = {}
        for token, quality in candidates:
            matches[token] = max(quality, matches.get(token, 0))
        return matches

    def _rarity(self, matching_schools: int) -> int:
        """Roughly log2 of how rare a word is: one more point each time it is
        half as common. A word in every school scores 1."""
        if not matching_schools:
            return 0
        return (len(self.schools) // matching_schools).bit_length()

    def _rank(
        self, scores: dict[int, int], word_matches: list[dict[str, int]], limit: int
    ) -> list[School]:
        positions_by_score: dict[int, list[int]] = {}
        for position, score in scores.items():
            positions_by_score.setdefault(score, []).append(position)

        def similarity(tokens: set[str]) -> float:
            """Jaccard similarity of the query words and these words: matches
            over all distinct words, with partial matches counting partly."""
            matched = (
                sum(
                    max((matches.get(token, 0) for token in tokens), default=0)
                    for matches in word_matches
                )
                / EXACT
            )
            return matched / (len(word_matches) + len(tokens) - matched)

        def tie_break(position: int) -> tuple[float, float, int, str, str, str, str]:
            school = self.schools[position]
            return (
                -similarity(self._name_tokens[position]),
                -similarity(self._city_tokens[position]),
                len(self._name_tokens[position]),
                school.name,
                school.city,
                school.state,
                school.school_id,
            )

        results: list[School] = []
        shown = set()
        for score in sorted(positions_by_score, reverse=True):
            for position in sorted(positions_by_score[score], key=tie_break):
                school = self.schools[position]
                line = (school.name, school.city, school.state)
                if line in shown:
                    continue
                shown.add(line)
                results.append(school)
                if len(results) == limit:
                    return results
        return results


_default_index: SchoolIndex | None = None


def default_index() -> SchoolIndex:
    """The index over the bundled dataset, built on first use."""
    global _default_index
    if _default_index is None:
        _default_index = SchoolIndex(load_schools(), load_state_names())
    return _default_index


def format_results(query: str, results: list[School], seconds: float) -> str:
    """Results in the format the README shows."""
    lines = [f'Results for "{query}" (search took: {seconds:.3f}s)']
    for rank, school in enumerate(results, start=1):
        lines.append(f"{rank}. {school.name}")
        lines.append(f"{school.city}, {school.state}")
    if not results:
        lines.append("No matching schools.")
    return "\n".join(lines)


def search_schools(
    query: str, index: SchoolIndex | None = None, limit: int = RESULT_LIMIT
) -> list[School]:
    """Print and return the top matches for query.

    The index is built before the timer starts: the README allows loading and
    processing up front, and the reported time is the search alone.
    """
    if index is None:
        index = default_index()
    start = time.perf_counter()
    results = index.search(query, limit)
    elapsed = time.perf_counter() - start
    print(format_results(query, results, elapsed))
    return results
