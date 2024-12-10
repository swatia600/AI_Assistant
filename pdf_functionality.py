import PyPDF2
from transformers import T5Tokenizer, T5ForConditionalGeneration
import tkinter as tk
from tkinter import filedialog
import os
import common
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts.prompt import PromptTemplate

# Document loader and vector store modules for processing PDFs
from langchain.document_loaders import PyPDFDirectoryLoader
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document 
def open_file_or_folder_dialog():
    """Open a dialog to select multiple PDF files or an entire folder."""
    root = tk.Tk()
    root.withdraw()  # Hide the main Tkinter window
    root.attributes('-topmost', True)  # Ensure the dialog appears on top

    # Allow user to select multiple files
    files = filedialog.askopenfilenames(
        title="Select PDF Files:",
        filetypes=[("PDF files", "*.pdf")]
    )
    return list(files), 'files'


def read_pdf_files(file_paths):
    """Read and extract text from multiple PDF files."""
    full_text = ""
    for file_path in file_paths:
        with open(file_path, 'rb') as pdf:
            pdf_reader = PyPDF2.PdfReader(pdf)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:  # Avoid adding None if the page has no text
                    full_text += page_text
    return full_text

def process_data(full_text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=250, chunk_overlap=50)
    texts = text_splitter.split_text(full_text)
    embeddings = HuggingFaceEmbeddings(model_name="hkunlp/instructor-large")
    documents = [Document(page_content=text) for text in texts]
    db = FAISS.from_documents(documents, embeddings)
    return db

def read_pdf_and_answer(user_input):
    """Open a dialog for selecting files or folder, extract text, and answer questions."""
    print("Please select PDF files.")
    llm = common.LocalLLM()
    selection, selection_type = open_file_or_folder_dialog()
    
    if not selection:
        print("No selection made.")
        return
    
    print("Extracting text from the selected PDF files...")
    if selection_type == 'files':
        context = read_pdf_files(selection)
        db = process_data(context)

    
    # Continue answering questions until the user exits
    chat_history = []
    print("You can now ask questions about the content in the PDFs. Type 'exit' to stop.")
    while True:
        question = input("Enter your question or write 'exit' to return to the main menu: ")
        if question.lower() == "exit":
            break
        # Refined prompt to limit the LLM to concise, focused answers only
        prompt = (
                f"You are an intelligent and knowledgeable AI assistant with expertise in analyzing and summarizing documents. "
                f"Your task is to assist the user by either summarizing the provided document or answering their specific questions. "
                f"When summarizing, focus on highlighting the main topics, key points, and essential details. When answering questions, provide precise, "
                f"clear, and accurate responses strictly based on the context of the provided documents.\n\n"
                f"Question: {question}"
        )

        conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=db.as_retriever(search_kwargs={'k': 4}),
        )
        
        result = conversation_chain.invoke({"question": prompt, "chat_history": chat_history})
        

        llm_response = result['answer'].strip() if result['answer'] else "{}"

        #print(f"Raw LLM response: {llm_response}")

        # Clean up the LLM response
        if llm_response.startswith("```") and llm_response.endswith("```"):
            llm_response = llm_response.strip("```").strip()
        #answer = common.ask_local_llm(prompt, context=context)
        chat_history.append((question, llm_response))
        print(f"Answer: {llm_response}")
