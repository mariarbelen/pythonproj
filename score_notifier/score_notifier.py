"""Exam Score Notifier.

Emails students their exam scores with personalized feedback: students
who scored 50 or below are pointed to the tutoring center, and students
who scored 90 or above get a gold star. Matching images are attached when
they exist in the images/ folder.

By default the program only previews the emails. Pass --send to actually
send them over SMTP; connection details come from environment variables
so no credentials live in the code.

Authors: Maria Rodriguez, George Lam (CS3C Lab)

Usage:
    python score_notifier.py students.csv            # preview
    python score_notifier.py students.csv --send     # send for real
    python score_notifier.py                         # enter students by hand
"""

import argparse
import csv
import getpass
import os
import re
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

IMAGE_DIR = Path(__file__).parent / "images"
TUTORING_THRESHOLD = 50
GOLD_STAR_THRESHOLD = 90

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def feedback_for(score):
    """Return (feedback text, image file name or None) for a score."""
    if score <= TUTORING_THRESHOLD:
        return "To do better next time, why not visit the tutoring center?", "tutoring.jpg"
    if score >= GOLD_STAR_THRESHOLD:
        return "Fantastic job! Keep it up.", "goldstar.jpg"
    return "Keep up the studying, and reach out during office hours if you have questions.", None


def build_message(sender, recipient, score, image_dir=IMAGE_DIR):
    """Build the email for one student."""
    feedback, image_name = feedback_for(score)

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = "Your exam score"
    msg.set_content(f"Your score on the last exam is {score}.\n\n{feedback}\n")

    if image_name:
        image_path = Path(image_dir) / image_name
        if image_path.is_file():
            msg.add_attachment(image_path.read_bytes(), maintype="image",
                               subtype="jpeg", filename=image_name)
    return msg


def parse_student(email, score_text):
    """Validate one student's email and score. Raises ValueError if invalid."""
    email = email.strip()
    if not EMAIL_PATTERN.match(email):
        raise ValueError(f"invalid email address: {email!r}")
    try:
        score = int(score_text)
    except ValueError:
        raise ValueError(f"score must be a whole number, got {score_text!r}") from None
    if not 0 <= score <= 100:
        raise ValueError(f"score must be between 0 and 100, got {score}")
    return email, score


def read_students_csv(path):
    """Read (email, score) pairs from a CSV with 'email' and 'score' columns.

    Invalid rows are reported and skipped.
    """
    students = []
    with open(path, newline="", encoding="utf-8") as file:
        for line_number, row in enumerate(csv.DictReader(file), start=2):
            try:
                students.append(parse_student(row.get("email") or "", row.get("score") or ""))
            except ValueError as error:
                print(f"Skipping line {line_number}: {error}", file=sys.stderr)
    return students


def read_students_interactively():
    """Prompt for students until a blank email is entered."""
    students = []
    print("Enter each student's email and score. Leave the email blank to finish.")
    while True:
        email = input("Student email: ").strip()
        if not email:
            return students
        try:
            students.append(parse_student(email, input("Score: ")))
        except ValueError as error:
            print(f"  {error}. Please try again.")


def preview(messages):
    for msg in messages:
        attachments = [part.get_filename() for part in msg.iter_attachments()]
        print("-" * 50)
        print(f"To:      {msg['To']}")
        print(f"Subject: {msg['Subject']}")
        if attachments:
            print(f"Attach:  {', '.join(attachments)}")
        print()
        print(msg.get_body(preferencelist=("plain",)).get_content().rstrip())
    print("-" * 50)
    print(f"{len(messages)} email(s) previewed. Run with --send to send them.")


def send(messages, config):
    password = os.environ.get("SMTP_PASSWORD") or getpass.getpass("SMTP password: ")
    with smtplib.SMTP(config["host"], config["port"]) as server:
        server.starttls()
        server.login(config["username"], password)
        for msg in messages:
            server.send_message(msg)
            print(f"Sent to {msg['To']}")


def smtp_config():
    """Read SMTP settings from environment variables."""
    sender = os.environ.get("SMTP_SENDER", "")
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "username": os.environ.get("SMTP_USERNAME", sender),
        "sender": sender,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Email students their exam scores.")
    parser.add_argument("csv_file", nargs="?", help="CSV file with 'email' and 'score' columns")
    parser.add_argument("--send", action="store_true", help="send the emails (default: preview only)")
    args = parser.parse_args(argv)

    config = smtp_config()
    if args.send and not config["sender"]:
        parser.error("set the SMTP_SENDER environment variable to your email address")

    if args.csv_file:
        students = read_students_csv(args.csv_file)
    else:
        students = read_students_interactively()
    if not students:
        print("No students to notify.")
        return

    sender = config["sender"] or "instructor@example.com"
    messages = [build_message(sender, email, score) for email, score in students]

    if args.send:
        send(messages, config)
    else:
        preview(messages)


if __name__ == "__main__":
    main()
