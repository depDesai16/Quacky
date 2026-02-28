from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
print("Google API key loaded")

chat = client.chats.create(model="gemini-2.5-flash")

def send_message_stream(user_input):
    """Stream one user prompt through Gemini chat and print chunks incrementally."""
    for chunk in chat.send_message_stream(user_input):
        print(chunk.text, end="", flush=True)
    print()

while True:
    user_input = input("Enter your prompt: ")
    if user_input == "exit":
        break
    send_message_stream(user_input)
#Gemini will say goodbye!
