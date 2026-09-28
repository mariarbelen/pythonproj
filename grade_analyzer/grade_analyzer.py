"""Grade Analyzer.

Reads a class gradebook CSV, computes each student's weighted course grade
and letter grade, flags students who may need help, and produces a class
report: summary statistics, a grade-distribution chart, and a scores file
that the Exam Score Notifier can use to email every student.

Gradebook format: one row per student with `name` and `email` columns plus
score columns (0-100). Columns starting with "hw" are homework; `midterm`
and `final` are exams. A blank score means the work was not turned in and
counts as 0.

Author: Maria Rodriguez

Usage:
    python grade_analyzer.py gradebook.csv
    python grade_analyzer.py gradebook.csv --drop-lowest --out report
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# How much each category counts toward the course grade.
WEIGHTS = {"homework": 0.30, "midterm": 0.30, "final": 0.40}

LETTER_CUTOFFS = [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F")]
LETTERS = [letter for _, letter in LETTER_CUTOFFS]

AT_RISK_SCORE = 70
AT_RISK_MISSING = 2


class GradebookError(ValueError):
    """Raised when the gradebook file has the wrong shape or bad values."""


def letter_grade(score):
    """Convert a 0-100 score to a letter grade."""
    for cutoff, letter in LETTER_CUTOFFS:
        if score >= cutoff:
            return letter
    return "F"


def homework_columns(df):
    return [column for column in df.columns if column.lower().startswith("hw")]


def load_gradebook(path):
    """Load and validate a gradebook CSV. Returns a DataFrame."""
    df = pd.read_csv(path)
    df.columns = [column.strip().lower() for column in df.columns]

    required = {"name", "email", "midterm", "final"}
    missing = required - set(df.columns)
    if missing:
        raise GradebookError(f"missing column(s): {', '.join(sorted(missing))}")
    if not homework_columns(df):
        raise GradebookError("no homework columns found (expected columns named hw1, hw2, ...)")
    if df.empty:
        raise GradebookError("the gradebook has no students")

    score_columns = homework_columns(df) + ["midterm", "final"]
    for column in score_columns:
        scores = pd.to_numeric(df[column], errors="coerce")
        bad = df[column].notna() & scores.isna()
        if bad.any():
            row = bad.idxmax() + 2  # +2: header line and 1-based numbering
            raise GradebookError(f"line {row}: {column} is not a number: {df.at[bad.idxmax(), column]!r}")
        if ((scores < 0) | (scores > 100)).any():
            row = ((scores < 0) | (scores > 100)).idxmax() + 2
            raise GradebookError(f"line {row}: {column} must be between 0 and 100")
        df[column] = scores
    return df


def compute_grades(df, drop_lowest=False):
    """Return a new DataFrame with per-student averages, grades and flags."""
    hw = homework_columns(df)
    result = df[["name", "email"]].copy()

    result["missing"] = df[hw + ["midterm", "final"]].isna().sum(axis=1)
    homework = df[hw].fillna(0)
    if drop_lowest and len(hw) > 1:
        # Drop each student's single lowest homework score.
        result["homework"] = (homework.sum(axis=1) - homework.min(axis=1)) / (len(hw) - 1)
    else:
        result["homework"] = homework.mean(axis=1)
    result["midterm"] = df["midterm"].fillna(0)
    result["final"] = df["final"].fillna(0)

    result["course_grade"] = sum(result[category] * weight for category, weight in WEIGHTS.items())
    result["course_grade"] = result["course_grade"].round(1)
    result["letter"] = result["course_grade"].apply(letter_grade)
    result["at_risk"] = (result["course_grade"] < AT_RISK_SCORE) | (result["missing"] >= AT_RISK_MISSING)
    return result.sort_values("course_grade", ascending=False).reset_index(drop=True)


def class_summary(df, grades):
    """Return a dict of class-wide statistics."""
    assignment_columns = homework_columns(df) + ["midterm", "final"]
    assignment_means = df[assignment_columns].fillna(0).mean()
    course = grades["course_grade"]
    return {
        "students": len(grades),
        "mean": course.mean(),
        "median": course.median(),
        "std": course.std(ddof=0),
        "high": course.max(),
        "low": course.min(),
        "letter_counts": grades["letter"].value_counts().reindex(LETTERS, fill_value=0),
        "hardest": assignment_means.idxmin(),
        "hardest_mean": assignment_means.min(),
    }


def format_report(grades, summary):
    lines = []
    lines.append(f"{'Student':<18}{'HW':>7}{'Midterm':>9}{'Final':>7}{'Grade':>8}  Letter")
    lines.append("-" * 57)
    for row in grades.itertuples():
        flag = "  <- needs help" if row.at_risk else ""
        lines.append(f"{row.name:<18}{row.homework:>7.1f}{row.midterm:>9.0f}{row.final:>7.0f}"
                     f"{row.course_grade:>8.1f}  {row.letter}{flag}")

    lines.append("")
    lines.append(f"Class of {summary['students']}: mean {summary['mean']:.1f}, "
                 f"median {summary['median']:.1f}, std dev {summary['std']:.1f}, "
                 f"range {summary['low']:.1f}-{summary['high']:.1f}")
    counts = summary["letter_counts"]
    lines.append("Grade distribution: " + ", ".join(f"{letter}: {counts[letter]}" for letter in LETTERS))
    lines.append(f"Hardest assignment: {summary['hardest']} (class average {summary['hardest_mean']:.1f})")

    at_risk = grades[grades["at_risk"]]
    if not at_risk.empty:
        lines.append("")
        lines.append(f"{len(at_risk)} student(s) may need help:")
        for row in at_risk.itertuples():
            reasons = []
            if row.course_grade < AT_RISK_SCORE:
                reasons.append(f"grade {row.course_grade:.1f}")
            if row.missing >= AT_RISK_MISSING:
                reasons.append(f"{row.missing} missing assignments")
            lines.append(f"  - {row.name} ({', '.join(reasons)})")
    return "\n".join(lines)


def plot_distribution(summary, path):
    """Save a bar chart of how many students earned each letter grade."""
    import matplotlib

    matplotlib.use("Agg")  # draw to a file; no window needed
    import matplotlib.pyplot as plt

    ink, muted, grid, surface, bar = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#2a78d6"
    counts = summary["letter_counts"]

    fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=150)
    fig.patch.set_facecolor(surface)
    ax.set_facecolor(surface)

    bars = ax.bar(LETTERS, counts.values, width=0.55, color=bar, zorder=2)
    ax.bar_label(bars, labels=[str(c) if c else "" for c in counts.values], padding=3,
                 color=ink, fontsize=10)

    ax.set_title(f"Grade distribution ({summary['students']} students)", loc="left",
                 color=ink, fontsize=12, pad=12)
    ax.set_ylabel("Students", color=muted, fontsize=9)
    ax.set_ylim(0, max(counts.max(), 1) * 1.2)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.grid(axis="y", color=grid, linewidth=0.8, zorder=0)
    ax.tick_params(colors=muted, labelsize=9, length=0)
    ax.tick_params(axis="x", labelcolor=ink, labelsize=11)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(muted)

    fig.tight_layout()
    fig.savefig(path, facecolor=surface)
    plt.close(fig)


def write_outputs(grades, summary, out_dir):
    """Write the full grade table, the notifier scores file and the chart."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    grades.to_csv(out_dir / "grades.csv", index=False, float_format="%.1f")
    # Same format the Exam Score Notifier reads: email,score (whole numbers).
    notifier = pd.DataFrame({"email": grades["email"], "score": grades["course_grade"].round().astype(int)})
    notifier.to_csv(out_dir / "scores_for_notifier.csv", index=False)
    plot_distribution(summary, out_dir / "grade_distribution.png")
    return out_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze a class gradebook.")
    parser.add_argument("gradebook", help="CSV file with name, email, hw*, midterm and final columns")
    parser.add_argument("--drop-lowest", action="store_true", help="drop each student's lowest homework score")
    parser.add_argument("--out", default="report", help="folder for output files (default: report)")
    args = parser.parse_args(argv)

    try:
        df = load_gradebook(args.gradebook)
    except (OSError, GradebookError) as error:
        sys.exit(f"Error: {error}")

    grades = compute_grades(df, drop_lowest=args.drop_lowest)
    summary = class_summary(df, grades)
    print(format_report(grades, summary))

    out_dir = write_outputs(grades, summary, args.out)
    print(f"\nSaved {out_dir / 'grades.csv'}, {out_dir / 'scores_for_notifier.csv'} "
          f"and {out_dir / 'grade_distribution.png'}")


if __name__ == "__main__":
    main()
