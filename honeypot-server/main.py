from ssh_server import start_ssh_server
from llm import LLM
from chatgpt import ChatGPT
'''
llama = LLM("../models/Meta-Llama-3.1-8B-Instruct")
start_ssh_server(llama)
'''
# gpt-4o-mini

llm = ChatGPT("gpt-4o-mini")
start_ssh_server(llm)
