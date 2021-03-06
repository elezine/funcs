
import smtplib, ssl

def send_alert(message, sender_email, password, recipient_email):
    '''
    Add this to your code to send an email alert (like if the code fails, for instance, with a try statement).
    '''
    port = 465
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', port, context=context) as server:
        server.login(str(sender_email), str(password))
        server.sendmail(str(sender_email),str(recipient_email),str(message))
