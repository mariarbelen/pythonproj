import pytest

import score_notifier
from score_notifier import build_message, feedback_for, parse_student, read_students_csv


@pytest.mark.parametrize(
    "score, image",
    [
        (0, "tutoring.jpg"),
        (50, "tutoring.jpg"),
        (51, None),
        (89, None),
        (90, "goldstar.jpg"),
        (100, "goldstar.jpg"),
    ],
)
def test_feedback_thresholds(score, image):
    assert feedback_for(score)[1] == image


def test_build_message_contents(tmp_path):
    msg = build_message("teacher@school.edu", "student@school.edu", 72, image_dir=tmp_path)
    assert msg["From"] == "teacher@school.edu"
    assert msg["To"] == "student@school.edu"
    assert "Your score on the last exam is 72." in msg.get_content()
    assert list(msg.iter_attachments()) == []


def test_build_message_attaches_image_when_present(tmp_path):
    (tmp_path / "goldstar.jpg").write_bytes(b"\xff\xd8fake-jpeg")
    msg = build_message("t@school.edu", "s@school.edu", 95, image_dir=tmp_path)
    attachments = list(msg.iter_attachments())
    assert [part.get_filename() for part in attachments] == ["goldstar.jpg"]
    assert "Fantastic job" in msg.get_body(preferencelist=("plain",)).get_content()


def test_build_message_skips_missing_image(tmp_path):
    msg = build_message("t@school.edu", "s@school.edu", 30, image_dir=tmp_path)
    assert "tutoring center" in msg.get_content()


@pytest.mark.parametrize(
    "email, score",
    [("bad-email", "80"), ("a@b.com", "eighty"), ("a@b.com", "101"), ("a@b.com", "-1")],
)
def test_parse_student_rejects_invalid_input(email, score):
    with pytest.raises(ValueError):
        parse_student(email, score)


def test_read_students_csv_skips_bad_rows(tmp_path, capsys):
    csv_file = tmp_path / "students.csv"
    csv_file.write_text("email,score\na@x.com,95\nnope,80\nb@x.com,abc\nc@x.com,40\n")
    assert read_students_csv(csv_file) == [("a@x.com", 95), ("c@x.com", 40)]
    assert capsys.readouterr().err.count("Skipping") == 2


def test_preview_does_not_send(tmp_path, capsys, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("preview mode must not connect to SMTP")

    monkeypatch.setattr(score_notifier.smtplib, "SMTP", fail)
    csv_file = tmp_path / "students.csv"
    csv_file.write_text("email,score\na@x.com,95\n")
    score_notifier.main([str(csv_file)])
    assert "1 email(s) previewed" in capsys.readouterr().out


def test_send_requires_sender(monkeypatch, tmp_path):
    monkeypatch.delenv("SMTP_SENDER", raising=False)
    with pytest.raises(SystemExit):
        score_notifier.main([str(tmp_path / "x.csv"), "--send"])


def test_send_uses_starttls_and_sends_each_message(tmp_path, monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port):
            self.calls = [("connect", host, port)]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            self.calls.append(("starttls",))

        def login(self, username, password):
            assert (username, password) == ("teacher@school.edu", "secret")

        def send_message(self, msg):
            assert ("starttls",) in self.calls
            sent.append(msg["To"])

    monkeypatch.setattr(score_notifier.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_SENDER", "teacher@school.edu")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    csv_file = tmp_path / "students.csv"
    csv_file.write_text("email,score\na@x.com,95\nb@x.com,40\n")
    score_notifier.main([str(csv_file), "--send"])
    assert sent == ["a@x.com", "b@x.com"]
