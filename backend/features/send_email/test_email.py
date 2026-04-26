"""Manual email-launch smoke script.

Import-safe so unittest discovery does not execute or fail on it.
"""


def main():
    from backend.tools import send_email

    result = send_email(
        "mikehud536@gmail.com",
        "Test Email from Script",
        "Hello! This is a test email from a Python script.",
    )
    print(result)


if __name__ == "__main__":
    main()
