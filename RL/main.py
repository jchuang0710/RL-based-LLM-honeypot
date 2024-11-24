from ssh_server import start_ssh_server
from LLM import LLM
from ChatGPT import ChatGPT
from Groq import Groq_LLM
'''
llama = LLM("../models/Meta-Llama-3.1-8B-Instruct")
start_ssh_server(llama)
'''
# gpt-4o-mini

llm = ChatGPT("gpt-4o-mini")
start_ssh_server(llm)
