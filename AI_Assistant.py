import time
import requests
import json
import re
from transformers import T5Tokenizer, T5ForConditionalGeneration
import email_functionality as email
import pdf_functionality
import calendar_functionality
import common

class MonicaAssistant:
    def __init__(self):
        print("I'm Monica, your AI assistant.")

        # Defining task mapping
        self.task_map = {
            "send email": email.handle_email_command,
            "schedule event": self.schedule_event,
            "handle document": pdf_functionality.read_pdf_and_answer,
            "web search": self.search_internet
        }
        # Supported task descriptions for clarification
        self.supported_tasks = {
            "send email": "sending someone an email, writing or mailing an email",
            "schedule event": "scheduling any event, meeting, reminder, or appointment in Google Calendar",
            "handle document": "reading, summarizing, explaining, or analyzing a PDF or document",
            "web search": "searching the internet for general questions, information, or random things"
        }

    def llm_do_task(self, user_input):
        # Prompt to classify the user input query: This way LLM will intelligently clissigy the user input
        question = (
            "Analyze the user's input and classify it as one of the following four tasks:\n"
            "1. 'send email': If the user's input is related to sending someone an email, mailing someone, "
            "or writing an email.\n"
            "2. 'schedule event': For any type of event, meeting, reminder, or task that needs to be scheduled "
            "in Google Calendar.\n"
            "3. 'handle document': For actions involving documents or PDFs such as reading, summarizing, "
            "explaining, analyzing, or answering questions based on a document.\n"
            "4. 'web search': For any general question or informational query, or other items not covered by the first three categories, "
            "such as 'What is pizza?', 'Tell me about climate change,' or 'Search for the latest news.'\n"
            "If the task does not match any of these, respond with exactly 'unrecognized'.\n\n"
            "Return only the task type if you recognize it or 'unrecognized'.\n"
            f"User input: '{user_input}'"
        )

        # Retrieve task type from Local LLM
        raw_task_type = common.ask_local_llm(question).strip()
        
        # Normalizing the task_type by removing extra quotes and parentheses to ensure no extra characters are there in the response
        task_type = re.sub(r'[^a-zA-Z\s]', '', raw_task_type).strip().lower()
        #print(f"Classified task: {task_type}")  # Debugging line to verify task type

        # Dynamically call the appropriate function based on the task_map
        task_function = self.task_map.get(task_type)
        #print("Task Function:", task_function)
        if task_function:
            task_function(user_input)
        else:
            self.ask_for_clarification(user_input)

    def schedule_event(self, user_input):
        # Use calendar_functionality to parse and schedule the event
        calendar_functionality.schedule_meeting(user_input)

    def search_internet(self, user_input):
        # Basic internet search using Google Custom Search API
        query = user_input
        API_KEY = "AIzaSyALRoHuSWv6InOQlZOj1lybx1EirzJsQB4"
        SEARCH_ENGINE_ID = "d143cde9d62664a94"
        url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}"

        try:
            response = requests.get(url)
            response.raise_for_status()
            results = response.json().get("items", [])
            if not results:
                print("No results found.")
                return
            # Display top results
            print("\n--- Search Results ---")
            for idx, item in enumerate(results[:5], 1):
                print(f"\nResult {idx}: {item.get('title')}\n{item.get('snippet')}\nURL: {item.get('link')}\n")
            print("--- End of Results ---\n")
        except requests.RequestException as e:
            print(f"An error occurred during the search: {e}")
    
    def ask_for_clarification(self, user_input):
        # Inform the user of the unrecognized task and prompt for further clarification
        task_options = ", ".join(f"{key}: {desc}" for key, desc in self.supported_tasks.items())
        print(
            f"I'm not able to recognize the task type for: '{user_input}'.\n"
            f"I can help with the following tasks:\n{task_options}\n"
            "Please provide more details or specify one of these tasks."
        )

# Initialize Monica
assistant = MonicaAssistant()

# Main loop
while True:
    try:
        user_input = input("Please enter a new task: ")
        tic = time.time()
        assistant.llm_do_task(user_input)
        latency = time.time() - tic
        print(f"\nLatency: {latency:.3f}s")
    except KeyboardInterrupt:
        print("\nExiting.\n")
        break
