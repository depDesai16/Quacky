import argparse
import sys

from client import QuackyClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Quacky client CLI")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--system", default=None)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    client = QuackyClient(args.base_url)
    chat = client.start_chat(system=args.system, model=args.model)
    chat_id = chat["chat_id"]

    print(f"Chat started: {chat_id}")
    print("Type 'exit' to quit.")

    while True:
        try:
            message = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.lower() in {"exit", "quit"}:
            break
        if not message:
            continue
        response = client.send_message(chat_id, message)
        print(response.get("text", ""))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
