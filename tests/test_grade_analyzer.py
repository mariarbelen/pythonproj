import pytest

import grade_analyzer as ga
from score_notifier import read_students_csv

HEADER = "name,email,hw1,hw2,midterm,final\n"


def write_gradebook(tmp_path, rows, header=HEADER):
    path = tmp_path / "gradebook.csv"
    path.write_text(header + "".join(row + "\n" for row in rows))
    return path


@pytest.mark.parametrize(
    "score, letter",
    [(100, "A"), (90, "A"), (89.9, "B"), (80, "B"), (79.9, "C"), (70, "C"), (60, "D"), (59.9, "F"), (0, "F")],
)
def test_letter_grade_cutoffs(score, letter):
    assert ga.letter_grade(score) == letter


def test_weighted_course_grade(tmp_path):
    path = write_gradebook(tmp_path, ["Ann,ann@x.com,80,100,70,95"])
    grades = ga.compute_grades(ga.load_gradebook(path))
    # homework 90 * 0.3 + midterm 70 * 0.3 + final 95 * 0.4 = 86
    assert grades.loc[0, "course_grade"] == 86.0
    assert grades.loc[0, "letter"] == "B"
    assert not grades.loc[0, "at_risk"]


def test_missing_work_counts_as_zero_and_is_flagged(tmp_path):
    path = write_gradebook(tmp_path, ["Ann,ann@x.com,,,90,90"])
    grades = ga.compute_grades(ga.load_gradebook(path))
    assert grades.loc[0, "homework"] == 0
    assert grades.loc[0, "missing"] == 2
    assert grades.loc[0, "at_risk"]  # 63 overall and 2 missing assignments


def test_drop_lowest_homework(tmp_path):
    path = write_gradebook(tmp_path, ["Ann,ann@x.com,40,100,100,100"])
    df = ga.load_gradebook(path)
    assert ga.compute_grades(df).loc[0, "homework"] == 70
    assert ga.compute_grades(df, drop_lowest=True).loc[0, "homework"] == 100


def test_results_sorted_best_first(tmp_path):
    path = write_gradebook(tmp_path, ["Low,l@x.com,50,50,50,50", "High,h@x.com,99,99,99,99"])
    grades = ga.compute_grades(ga.load_gradebook(path))
    assert list(grades["name"]) == ["High", "Low"]


def test_class_summary(tmp_path):
    path = write_gradebook(tmp_path, ["A,a@x.com,100,100,100,100", "B,b@x.com,50,70,60,60"])
    df = ga.load_gradebook(path)
    summary = ga.class_summary(df, ga.compute_grades(df))
    assert summary["students"] == 2
    assert summary["mean"] == pytest.approx(80)
    assert summary["letter_counts"]["A"] == 1
    assert summary["letter_counts"]["D"] == 1
    assert summary["hardest"] == "hw1"


@pytest.mark.parametrize(
    "header, row, message",
    [
        ("name,email,hw1,final\n", "A,a@x.com,90,90", r"missing column\(s\): midterm"),
        ("name,email,midterm,final\n", "A,a@x.com,90,90", "no homework columns"),
        (HEADER, "A,a@x.com,90,abc,90,90", "hw2 is not a number"),
        (HEADER, "A,a@x.com,90,105,90,90", "between 0 and 100"),
    ],
)
def test_load_gradebook_rejects_bad_files(tmp_path, header, row, message):
    path = write_gradebook(tmp_path, [row], header=header)
    with pytest.raises(ga.GradebookError, match=message):
        ga.load_gradebook(path)


def test_outputs_work_with_score_notifier(tmp_path):
    path = write_gradebook(tmp_path, ["Ann,ann@x.com,80,100,70,95", "Bo,bo@x.com,60,60,55,58"])
    df = ga.load_gradebook(path)
    grades = ga.compute_grades(df)
    out = ga.write_outputs(grades, ga.class_summary(df, grades), tmp_path / "report")

    assert (out / "grade_distribution.png").stat().st_size > 0
    assert (out / "grades.csv").exists()
    assert read_students_csv(out / "scores_for_notifier.csv") == [("ann@x.com", 86), ("bo@x.com", 58)]


def test_main_reports_errors_cleanly(tmp_path):
    with pytest.raises(SystemExit, match="Error"):
        ga.main([str(tmp_path / "does_not_exist.csv")])


def test_main_on_sample_gradebook(tmp_path, capsys):
    ga.main([str(ga.Path(ga.__file__).parent / "gradebook.csv"), "--out", str(tmp_path)])
    output = capsys.readouterr().out
    assert "Class of 20" in output
    assert "needs help" in output
