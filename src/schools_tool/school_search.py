"""Part 2: find schools by name, city, and state from a plain-text query.

Ranking rules, in order:

1. Each query word scores the schools it matches. A word matches a school
   when it equals a word in the school's name, city, or state name, or is
   the abbreviation or expansion of one ("elementary" finds ELEM). For
   partial credit it also matches words it starts ("highl" finds HIGHLAND).
   A word that matches nothing that way may match a word one typo away
   ("kuskokwin" finds KUSKOKWIM) for less. A postal code counts only as the
   last word ("foley high al"), where it means only the state, and
   connecting words such as "in" and "of" are skipped, so "high school in
   chicago" means Chicago, not Indiana.
2. Rare words count for more than common ones, so "foley" decides more than
   "high", and "school", which most names contain, barely counts.
3. Ties go, in order, to the school whose name has the fewest words the
   query doesn't match; with more query word pairs side by side in its name
   or city ("park forest" fits PARK FOREST, not FOREST PARK); spelled as
   typed rather than abbreviated (ELEMENTARY over ELEM); with more query
   words in its name; whose city best matches; with the shorter name;
   then alphabetically. So HIGHLAND PARK ELEMENTARY SCHOOL comes before
   schools located in Highland Park, CALIFORNIA HIGH in San Ramon before SAN
   RAMON VALLEY HIGH in Danville, THE ACADEMY in San Jose before SAN JOSE
   HIGH ACADEMY, and RANCHO CUCAMONGA MIDDLE before CUCAMONGA MIDDLE.
4. Results with the same name, city, and state are shown once.
"""

import time
from collections.abc import Iterator

from schools_tool.dataset import School, load_schools, load_state_names

RESULT_LIMIT = 3

# How well a query word matches an indexed word. Score points are the match
# quality times the word's rarity; an abbreviation scores like the word
# itself and loses only ties to the spelling as typed.
EXACT = 10
ABBREVIATION = 9
PREFIX = 6
TYPO = 5

# Words shorter than these are matched exactly only; "in" should not match
# every word that starts with "in".
MIN_PREFIX_LENGTH = 3
MIN_TYPO_LENGTH = 4

# Abbreviations common in school and city names (2,229 names say ELEM). A
# query word matches both the word as typed and its abbreviation or
# expansion, so "elementary" finds ELEM and "elem" finds ELEMENTARY.
ABBREVIATIONS = {
    "ACAD": ("ACADEMY",),
    "CO": ("COUNTY",),
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
    "ST": ("SAINT",),
}

# Query words that only connect others ("high school in chicago"). They are
# skipped unless the query has nothing else, and don't count against a name
# that contains them (TOP OF THE KUSKOKWIM SCHOOL).
STOPWORDS = {"A", "AN", "AND", "AT", "FOR", "IN", "NEAR", "OF", "ON", "THE", "TO"}

# Dropped inside words: "MARY'S", "RIVER`S" (10 names use a backtick).
APOSTROPHES = "'’‘`´ʼ"

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

    Apostrophes are dropped ("MARY'S" -> "MARYS"), other punctuation
    separates words ("COLLINS-RIVERSIDE" -> "COLLINS", "RIVERSIDE"), and
    numbers lose leading zeros ("044" -> "44").
    """
    text = text.upper()
    for apostrophe in APOSTROPHES:
        text = text.replace(apostrophe, "")
    spaced = "".join(char if char.isalnum() else " " for char in text)
    return [
        word.lstrip("0") or "0" if word.isdigit() else word for word in spaced.split()
    ]


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


def content_words(text: str) -> tuple[str, ...]:
    """The words of text other than stopwords, in order."""
    return tuple(word for word in tokenize(text) if word not in STOPWORDS)


def score_points(quality: int) -> int:
    return EXACT if quality == ABBREVIATION else quality


class QueryFit:
    """How closely a school's name or city words fit a query, for breaking
    ties between schools with the same score. Measures are in match-quality
    points, so EXACT stands for one whole word."""

    def __init__(
        self, word_matches: dict[str, dict[str, int]], word_pairs: list[tuple[str, str]]
    ) -> None:
        # query word -> {indexed token it matches: match quality}
        self.word_matches = word_matches
        # consecutive query words, in order
        self.word_pairs = word_pairs
        # indexed token -> the best quality any query word matched it with
        self.token_quality: dict[str, int] = {}
        for matches in word_matches.values():
            for token, quality in matches.items():
                self.token_quality[token] = max(
                    quality, self.token_quality.get(token, 0)
                )

    def matched(self, words: tuple[str, ...]) -> int:
        """The query words these words contain; partial matches count partly
        and abbreviations fully."""
        return sum(
            max((score_points(matches.get(word, 0)) for word in words), default=0)
            for matches in self.word_matches.values()
        )

    def unmatched(self, distinct_words: tuple[str, ...]) -> int:
        """The words the query doesn't match; partial matches count partly
        and abbreviations not at all."""
        return EXACT * len(distinct_words) - sum(
            score_points(self.token_quality.get(word, 0)) for word in distinct_words
        )

    def abbreviated(self, distinct_words: tuple[str, ...]) -> int:
        """How many of these words matched only as an abbreviation of a query
        word (ELEM for "elementary")."""
        return sum(
            self.token_quality.get(word) == ABBREVIATION for word in distinct_words
        )

    def phrases(self, words: tuple[str, ...]) -> int:
        """How many pairs of consecutive query words appear side by side, in
        order, in these words ("park forest" in PARK FOREST, not FOREST PARK)."""
        if not self.word_pairs:
            return 0
        adjacent = list(zip(words, words[1:], strict=False))
        return sum(
            any(
                self.word_matches[first].get(left)
                and self.word_matches[second].get(right)
                for left, right in adjacent
            )
            for first, second in self.word_pairs
        )


class SchoolIndex:
    """An inverted index over schools, built once so each search is fast."""

    def __init__(self, schools: list[School], state_names: dict[str, str]) -> None:
        self.schools = schools
        # Per school, for breaking ties: the words of its name and city in
        # order without stopwords, and each once
        self._name_words = [content_words(school.name) for school in schools]
        self._city_words = [content_words(school.city) for school in schools]
        self._distinct_name_words = [tuple(dict.fromkeys(w)) for w in self._name_words]
        self._distinct_city_words = [tuple(dict.fromkeys(w)) for w in self._city_words]

        # token -> positions in self.schools of the schools containing it
        self._postings: dict[str, list[int]] = {}
        # postal code -> positions of the schools in that state
        self._schools_by_state: dict[str, list[int]] = {}
        for position, school in enumerate(schools):
            searchable = (
                f"{school.name} {school.city} {state_names.get(school.state, '')}"
            )
            for token in set(tokenize(searchable)):
                self._postings.setdefault(token, []).append(position)
            self._schools_by_state.setdefault(school.state, []).append(position)

        # prefix -> longer tokens that start with it
        self._completions: dict[str, list[str]] = {}
        for token in self._postings:
            for end in range(MIN_PREFIX_LENGTH, len(token)):
                self._completions.setdefault(token[:end], []).append(token)
        self._longest_token = max(map(len, self._postings), default=0)

    def search(self, query: str, limit: int = RESULT_LIMIT) -> list[School]:
        words = tokenize(query)
        if limit < 1 or not words:
            return []
        last = len(words) - 1
        searched = [
            word
            for i, word in enumerate(words)
            if word not in STOPWORDS or (i == last and word in self._schools_by_state)
        ] or words

        scores: dict[int, int] = {}
        # For each query word, the indexed tokens it matches and how well
        word_matches: dict[str, dict[str, int]] = {}
        for word in dict.fromkeys(searched):
            state = self._schools_by_state.get(word) if word == words[-1] else None
            matches = self._matching_tokens(word)
            if state:
                # A trailing postal code means the state: "lamar co" is
                # Lamar, Colorado, not LAMAR COUNTY.
                matches = {t: q for t, q in matches.items() if q == EXACT}
            word_matches[word] = matches

            points_by_position = self._points_by_position(matches)
            for position in state or []:
                points_by_position[position] = EXACT
            weight = self._rarity(len(points_by_position))
            for position, points in points_by_position.items():
                scores[position] = scores.get(position, 0) + points * weight
        word_pairs = list(zip(searched, searched[1:], strict=False))
        return self._rank(scores, word_matches, word_pairs, limit)

    def _points_by_position(self, matches: dict[str, int]) -> dict[int, int]:
        """Points per school for one query word: its best match, unweighted."""
        points_by_position: dict[int, int] = {}
        for token, quality in matches.items():
            points = score_points(quality)
            for position in self._postings[token]:
                if points_by_position.get(position, 0) < points:
                    points_by_position[position] = points
        return points_by_position

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
        # A word longer than any indexed word plus one can't be one typo
        # away, and its edits would be slow to generate.
        if not candidates and MIN_TYPO_LENGTH <= len(word) <= self._longest_token + 1:
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
        self,
        scores: dict[int, int],
        word_matches: dict[str, dict[str, int]],
        word_pairs: list[tuple[str, str]],
        limit: int,
    ) -> list[School]:
        positions_by_score: dict[int, list[int]] = {}
        for position, score in scores.items():
            positions_by_score.setdefault(score, []).append(position)

        fit = QueryFit(word_matches, word_pairs)

        def name_extras(position: int) -> int:
            """Name words the query doesn't match."""
            return fit.unmatched(self._distinct_name_words[position])

        def tie_break(
            position: int,
        ) -> tuple[int, int, int, int, int, int, str, str, str, str]:
            school = self.schools[position]
            name_words = self._name_words[position]
            city_words = self._city_words[position]
            return (
                -(fit.phrases(name_words) + fit.phrases(city_words)),
                fit.abbreviated(self._distinct_name_words[position]),
                -fit.matched(name_words),
                -fit.matched(city_words),
                fit.unmatched(self._distinct_city_words[position]),
                len(name_words),
                school.name,
                school.city,
                school.state,
                school.school_id,
            )

        def in_tie_break_order(tied: list[int]) -> Iterator[int]:
            # Thousands of schools can share a score (a query of just
            # "school"), so group them by name extras first and fully sort
            # only the groups that get used.
            by_extras: dict[int, list[int]] = {}
            for position in tied:
                by_extras.setdefault(name_extras(position), []).append(position)
            for extras in sorted(by_extras):
                yield from sorted(by_extras[extras], key=tie_break)

        results: list[School] = []
        shown = set()
        for score in sorted(positions_by_score, reverse=True):
            for position in in_tie_break_order(positions_by_score[score]):
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


def format_location(school: School) -> str:
    return f"{school.city}, {school.state}" if school.city else school.state


def format_results(query: str, results: list[School], seconds: float) -> str:
    """Results in the format the README shows."""
    lines = [f'Results for "{query}" (search took: {seconds:.3f}s)']
    for rank, school in enumerate(results, start=1):
        lines.append(f"{rank}. {school.name}")
        lines.append(format_location(school))
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
