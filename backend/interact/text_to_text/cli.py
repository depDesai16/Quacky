import argparse
import sys

from backend.client import QuackyClient

def load_system_prompt():
    with open("backend/system_prompt.txt", "r", encoding="utf-8") as f:
        return f.read()

def main() -> int:
    parser = argparse.ArgumentParser(description="Quacky client CLI")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--system", default=None)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    client = QuackyClient(args.base_url)

    system_prompt = args.system or load_system_prompt()

    chat = client.start_chat(system=system_prompt, model=args.model)
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
        if "error" in response:
            print(f"[Error] {response['error']}")
            continue

        print(response.get("text", ""))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
