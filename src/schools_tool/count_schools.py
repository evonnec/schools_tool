"""Part 1: counts over the school dataset."""

import csv
from collections.abc import Callable, Iterable
from pathlib import Path

from schools_tool.dataset import School, load_schools

# A city is a (city name, state) pair: SPRINGFIELD, IL and SPRINGFIELD, CO are
# different cities.
City = tuple[str, str]


def count_by[K](schools: Iterable[School], key: Callable[[School], K]) -> dict[K, int]:
    counts: dict[K, int] = {}
    for school in schools:
        group = key(school)
        counts[group] = counts.get(group, 0) + 1
    return counts


def total_school_count(schools: Iterable[School]) -> int:
    """One per school record, like the other counts; load_schools keeps one
    record per school ID."""
    return sum(1 for _ in schools)


def schools_per_state(schools: Iterable[School]) -> dict[str, int]:
    return count_by(schools, lambda school: school.state)


def schools_per_metro_locale(schools: Iterable[School]) -> dict[str, int]:
    """Schools per metro-centric locale code; "N" means no locale assigned."""
    return count_by(schools, lambda school: school.metro_locale)


def schools_per_city(schools: Iterable[School]) -> dict[City, int]:
    """Schools per city; schools with no known city are left out."""
    with_city = (school for school in schools if school.city)
    return count_by(with_city, lambda school: (school.city, school.state))


def cities_with_most_schools(schools: Iterable[School]) -> tuple[list[City], int]:
    """Every city tied for the most schools, alphabetically, and that count."""
    per_city = schools_per_city(schools)
    if not per_city:
        return [], 0
    most = max(per_city.values())
    return sorted(city for city, count in per_city.items() if count == most), most


def unique_city_count(schools: Iterable[School]) -> int:
    return len(schools_per_city(schools))


def format_city(city: City) -> str:
    name, state = city
    return f"{name}, {state}"


def format_counts(schools: list[School]) -> str:
    """The Part 1 report in the format the README shows."""
    lines = [f"Total Schools: {total_school_count(schools)}", "Schools by State:"]
    for state, count in sorted(schools_per_state(schools).items()):
        lines.append(f"{state}: {count}")

    lines.append("Schools by Metro-centric locale:")
    for locale, count in sorted(schools_per_metro_locale(schools).items()):
        lines.append(f"{locale}: {count}")

    cities, most = cities_with_most_schools(schools)
    if not cities:
        lines.append("City with most schools: none")
    elif len(cities) == 1:
        lines.append(
            f"City with most schools: {format_city(cities[0])} ({most} schools)"
        )
    else:
        tied = "; ".join(format_city(city) for city in cities)
        lines.append(f"Cities with most schools: {tied} ({most} schools each)")

    lines.append(
        f"Unique cities with at least one school: {unique_city_count(schools)}"
    )
    return "\n".join(lines)


def print_counts(schools: list[School] | None = None) -> None:
    """Print the Part 1 report, loading the bundled dataset by default."""
    if schools is None:
        schools = load_schools()
    print(format_counts(schools))


def write_counts(schools: list[School], output_dir: Path) -> list[Path]:
    """Write the counts as CSV files in output_dir and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cities, most = cities_with_most_schools(schools)
    # Most schools first, then alphabetically
    city_rows = sorted(
        (
            (city, state, count)
            for (city, state), count in schools_per_city(schools).items()
        ),
        key=lambda row: (-row[2], row[0], row[1]),
    )
    tables: dict[str, tuple[list[str], list[tuple[object, ...]]]] = {
        "summary.csv": (
            ["metric", "value"],
            [
                ("total_schools", total_school_count(schools)),
                ("unique_cities", unique_city_count(schools)),
                ("most_schools_in_a_city", most),
                ("cities_with_most_schools", "; ".join(map(format_city, cities))),
            ],
        ),
        "schools_by_state.csv": (
            ["state", "school_count"],
            sorted(schools_per_state(schools).items()),
        ),
        "schools_by_metro_locale.csv": (
            ["metro_locale", "school_count"],
            sorted(schools_per_metro_locale(schools).items()),
        ),
        "schools_by_city.csv": (["city", "state", "school_count"], list(city_rows)),
    }
    written = []
    for file_name, (header, rows) in tables.items():
        path = output_dir / file_name
        with path.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(header)
            writer.writerows(rows)
        written.append(path)
    return written
