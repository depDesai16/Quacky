from google import genai
from dotenv import load_dotenv
import os

load_dotenv()


def get_response_stream(user_input):
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents=user_input
    ):
        print(chunk.text, end="", flush=True)
    print() 

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
print("Google API key loaded")
while True:
    user_input = input("Enter your prompt: ")
    get_response_stream(user_input)
    if user_input == "exit":
        break
#Gemini will say goodbye!
