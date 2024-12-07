import ollama
from transformers import T5Tokenizer, T5ForConditionalGeneration

# Initialize the tokenizer and model for natural language processing
checkpoint = "google/flan-t5-large"
tokenizer = T5Tokenizer.from_pretrained(checkpoint)
model = T5ForConditionalGeneration.from_pretrained(checkpoint, device_map='auto')

#  Email database: new email ids to be added here
emailDataBase = {
    # "Steve Jobs": "sjobs@apple.com",
    # "Bill Gates": "bgates@microsoft.com",
    # "Sundar Pichai": "spichai@google.com"
    "Vicky": "varunsahni0786@gmail.com",
    "Vardan": "varunsahni10134@gmail.com",
    "Varun": "varunsahni260897@gmail.com",
    "Swati": "swatia600@gmail.com"
}

from difflib import get_close_matches

def find_recipient_email_with_llm(recipient_name):
    # Find the closest match for recipient_name in emailDataBase using difflib
    closest_matches = get_close_matches(recipient_name.lower(), emailDataBase.keys(), n=1, cutoff=0.6)
    
    if closest_matches:
        best_match = closest_matches[0]
        matched_email = emailDataBase[best_match]
        confirmation = input(f"Is '{best_match}' with email '{matched_email}' correct? (yes/no): ")
        
        if confirmation.lower() == 'yes':
            return matched_email
        else:
            return input("Please input the email id for recipient: ")
    else:
        return input("No close matches found in email database. Please input the email id : ")

def ask_local_llm(question, context=None):
    Model = 'llama3.2:3b'
    
    # Adding context to the prompt
    prompt = f"Context: {context}\n\nQuestion: {question}" if context else question

    # Sending the prompt to the model
    response = ollama.chat(model=Model, messages=[{'role': 'user', 'content': prompt}])
    Response = response.get('message', {}).get('content', 'No response content')
    # print("Ollama: ", Response) //Debug statement

    return Response