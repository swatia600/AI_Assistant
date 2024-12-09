import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
import common as common 
import re

# SMTP email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_ADDRESS = 'swatia600@gmail.com'
EMAIL_PASSWORD = 'pass'

# Parse the command using the local LLM
def parse_command_with_llm(command):
    question = (
        f"I need to draft an email based on the following user input. Please analyze the input to identify the recipient's name and the main message content.\n\n"
        f"Return the output strictly in **JSON format** with two fields: 'recipient' and 'content'. Do not include any additional text, explanations, or code.\n\n"
        f"Instructions:\n"
        f"- Parse only the recipient's name and the message content from the input.\n"
        f"- If the input does not specify a recipient's name or email content, set the respective JSON field empty.\n\n"
        f"Examples:\n"
        f"1. User Input: 'send a thank you email to Steve Jobs for the opportunity'\n"
        f"   Expected Output: {{'recipient': 'Steve Jobs', 'content': 'Thank you for the opportunity.'}}\n\n"
        f"2. User Input: 'write an email to Bill to say congratulations on the new release'\n"
        f"   Expected Output: {{'recipient': 'Bill', 'content': 'Congratulations on the new release.'}}\n\n"
        f"3. User Input: 'write an email to Tom'\n"
        f"   Expected Output: {{'recipient': 'Tom', 'content': ''}}\n\n"
        f"Now, analyze the command: '{command}'"
    )
    
    response = common.ask_local_llm(question)
    try:
        # Attempt to parse the response as JSON using eval, or better yet use json.loads if it is valid JSON.
        parsed_content = eval(response.strip())
        recipient = parsed_content.get("recipient")
        content = parsed_content.get("content")
        #print(parsed_content)
        return recipient, content
    except (SyntaxError, ValueError):
        print("Failed to parse the LLM response. Check the response format.")
        return None, None


# Generate email content using the local LLM
import json

import json
import re

def generate_email_content(recipient_name, content, context_detail):

    #print("context_detail: ", context_detail)
    #Using Local LLm to generate the subject and body of the email based on the prompt-  This will help in intelligent email creation
    question = (
        f"Write a professional email to {recipient_name}. Generate an appropriate subject line and relevant body of the email based on the following input: '{content}' and '{context_detail}'.\n"
        f"The body should start with a proper salutation including the recipient's name, followed by two line breaks, and then the remaining body content. Always end the body with '\\n\\nRegards,\\n\\nVarun'.\n"
        f"Ensure all line breaks are represented as '\\n' and special characters are properly escaped in the JSON.\n"
        f"Return the output strictly in **JSON format** with two fields: 'subject' and 'body'. Do not include any additional text, explanations, or code.\n\n"
        f"Example of the required JSON format:\n"
        f"{{\n  \"subject\": \"Your subject here\",\n  \"body\": \"Dear RecipientName,\\n\\nYour email body here.\\n\\nRegards,\\n\\Swati\"\n}}\n"
        f"Output the JSON object only, with no extra text."
    )
    response = common.ask_local_llm(question)
    #print("Response: ", response)

    try:
        # Extracting JSON object from the response
        json_str_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_str_match:
            json_str = json_str_match.group(0)
            # Replacing actual newlines with escaped newlines for JSON parsing
            json_str = json_str.replace('\n', '\\n')
            parsed_content = json.loads(json_str)
            
            # Extracting subject and body
            subject = parsed_content.get("subject", "No Subject").strip()
            body = parsed_content.get("body", "No Content").strip()
            formatted_body = body.replace('\\n', '\n')
            
            if not subject:
                subject = "No Subject Provided"

            return subject, formatted_body
        else:
            print("Failed to extract JSON from the LLM response.")
            return "No Subject", "No Content"

    except json.JSONDecodeError as e:
        #print(f"Failed to parse the LLM response. Error: {e}")
        #print(f"LLM response was: {response}")
        return "No Subject", "No Content"

# Function to send email
def send_email(subject, recipient_email, email_body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(email_body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())

        print("Email sent successfully.")
    except Exception as e:
        print("Failed to send email:", str(e))

# Main function to handle email sending with draft confirmation
def handle_email_command(command):

    if "reply" in command.lower() or "respond" in command.lower():
        print("Replying to any email functionality is not yet enabled. Please provide any other task. ")
        return 

    recipient_name, content = parse_command_with_llm(command)

    if not recipient_name:
        recipient_name = input("Missing information detected in recipient, please specify the reciepient name: ")

    recipient_email = common.find_recipient_email_with_llm(recipient_name)
    context_detail = ''
    if not content:
        context_detail = input("Missing information detected in the content of the email, please specify the email context: ")
    if recipient_email:
        while True:
            # Generate the email draft
            subject, email_body = generate_email_content(recipient_name, content, context_detail)
            print("\n--- Email Draft ---")
            print(f"To: {recipient_email}")
            print(f"Subject: {subject}")
            print(f"Body:\n\n{email_body}")
            print("--- End of Draft ---\n")
            
            # Confirm draft with the user
            confirmation = input("Does the email draft look correct? (yes/no): ")
            
            if confirmation.lower() == 'yes':
                send_email(subject, recipient_email, email_body)
                break  # Exit the loop if the email is confirmed
            else:
                print("Let's modify the details to improve the draft.")
                # Ask for additional details to refine the draft
                additional_context = input("Please specify additional details:")
                
                context_detail += " " + additional_context  # Append new context for the next draft
    else:
        print("Could not confirm recipient email.")