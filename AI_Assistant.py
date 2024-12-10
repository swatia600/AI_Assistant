import time
import requests
import json
import re
from transformers import T5Tokenizer, T5ForConditionalGeneration
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
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
        self.llm = common.LocalLLM()
        self.classification_chain = self._create_classification_chain()

    def _create_classification_chain(self):
        # Define the prompt for task classification
        prompt_template = PromptTemplate(
            input_variables=["user_input"],
            template=(
                "Analyze the user's input and classify it as one of the following four tasks:\n"
                "1. 'send email': For email-related actions (e.g., write an email, send an email).\n"
                "2. 'schedule event': For calendar events (e.g., schedule a meeting, add a reminder).\n"
                "3. 'handle document': For actions involving PDFs or documents (e.g., read pdf, summarize document).\n"
                "4. 'web search': For general informational queries (e.g., search for information, look up news).\n"
                "If the input does not match any of these, respond with 'unrecognized'.\n\n"
                "Return only the task type(eg. send email, schedule event, handle document, web search) without additional explanation.\n\n"
                "User input: {user_input}"
            )
        )
        #print(prompt_template)
        return LLMChain(llm=self.llm, prompt=prompt_template)
    
    def llm_do_task(self, user_input):
        # Run the classification chain to get the task type
        result = self.classification_chain.invoke(user_input)
        #print(result)
        task_type = result['text'].strip().lower()
        task_function = self.task_map.get(task_type)
        print(task_function)
        # Execute the identified task or ask for clarification
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
