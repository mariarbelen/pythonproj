## CS3C LAB 3.35.55: Maria Rodriguez, George Lam
# This program allows you to notify multiple students of their
# test scores via e-mail

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

attachment = 'tutoring.jpg'
attachment2 = 'goldstar.jpg'

sender = "cslab944@gmail.com"
username = "python"
password = input("Password:")
host = "smtp.gmail.com"
port = 587

recipient = input("Student email: ")
score = int(input("Score: "))
body = "Your score on the last exam is " + str(score) + "\n"
if score <= 50:
    file = open("tutoring.jpg", "rb")
    img = MIMEImage(file.read())
    file.close()
    msg.attach(img)
    body = body + "To do better next time, why not visit the tutoring center?"
elif score >= 90:
    file = open("goldstar.jpg", "rb")
    img = MIMEImage(file.read())
    file.close()
    msg.attach(img)
    body = body + "Fantastic job! Keep it up."

msg = MIMEMultipart()
msg.add_header("From", sender)
msg.add_header("To", recipient)
msg.add_header("Subject", "Exam score")
msg.attach(MIMEText(body, "plain"))

server = smtplib.SMTP(host, port)
server.starttls()
server.login(username, password)
server.send_message(msg)
server.quit()

