import platform
import subprocess
import webbrowser
import urllib.parse


def send_email(email_address: str, subject: str, body: str) -> str:
    """
    Opens the user's email client with a prefilled email.
    Tries Outlook on Windows/macOS; falls back to default mail client.
    Handles multi-line email bodies safely.
    """
    system = platform.system()

    try:
        if system == "Windows":
            try:
                import win32com.client
                outlook = win32com.client.Dispatch("Outlook.Application")
                mail = outlook.CreateItem(0)
                mail.To = email_address
                mail.Subject = subject
                mail.Body = body
                mail.Display()
                return "Opened Outlook with email on Windows"
            except ImportError:
                query = urllib.parse.urlencode({"subject": subject, "body": body})
                webbrowser.open(f"mailto:{email_address}?{query}")
                return "Opened default email client on Windows (win32com not installed)"

        elif system == "Darwin":
            subject_safe = subject.replace('"', '\\"')
            email_safe = email_address.replace('"', '\\"')

            body_lines = body.splitlines()
            body_safe = '\\n'.join(line.replace('"', '\\"') for line in body_lines)

            applescript = f'''
            tell application "Microsoft Outlook"
                set newMessage to make new outgoing message
                set subject of newMessage to "{subject_safe}"
                set content of newMessage to "{body_safe}"
                make new recipient at end of to recipients of newMessage with properties {{email address:{{address:"{email_safe}"}}}}
                open newMessage
            end tell
            '''
            subprocess.run(["osascript", "-e", applescript])
            return "Opened Outlook on macOS"

        else:
            query = urllib.parse.urlencode({"subject": subject, "body": body})
            webbrowser.open(f"mailto:{email_address}?{query}")
            return "Opened default email client"

    except Exception as e:
        return f"Error opening email client: {e}"
