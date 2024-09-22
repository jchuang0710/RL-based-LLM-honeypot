import torch
import gc
import re
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline
)

class LLM:
    def __init__(self, model_name="NousResearch/Meta-Llama-3-8B-Instruct"):
        gc.collect()
        torch.cuda.empty_cache()
        print("Cleared GPU...")
        self.DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.BASE_MODEL_NAME = model_name
        self.SYSTEM_PROMPT = "I want you to act as a ubuntu terminal which have join into ad domain 'hslab.com'. I will type commands and you will reply with what the terminal should show. I want you only to reply with the terminal output in plaintest, and nothing else.  Some commands will be composed of multiple instructs, please reply them in order and reply need to consider the previous instructs.  Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output. All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets {like this}. You should print the terminal output first, final is the prompt for input, the prompt should follow this format 'user-name@computer-name:curr-dir$ '."
        print('Device:',self.DEVICE)
        # Model configuration
        self.pipeline = pipeline(
            "text-generation",
            model=self.BASE_MODEL_NAME,
            tokenizer=self.BASE_MODEL_NAME,
            model_kwargs={"torch_dtype": torch.bfloat16},
            device=self.DEVICE,
        )

        print("Loaded Model: ", self.BASE_MODEL_NAME)

    def answer(self, query, log_history=[], max_tokens=4096, temperature=0.01, top_p=0.8):

        message_history = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message_history.append({"role": "user", "content": item})
                else:
                    message_history.append({"role": "assistant", "content": item})

        user_prompt = message_history + [{"role": "user", "content": query}]
        prompt = self.pipeline.tokenizer.apply_chat_template(
            user_prompt, tokenize=False, add_generation_prompt=True
        )
        outputs = self.pipeline(
            prompt,
            max_new_tokens=max_tokens,
            pad_token_id=self.pipeline.tokenizer.eos_token_id,
            eos_token_id=self.pipeline.tokenizer.eos_token_id,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
        )
        response = outputs[0]["generated_text"][len(prompt):]
        
        # remove unnecessary quotes
        if response.startswith("plaintext\n"):
            response = response[9:0]
        elif response.startswith("```") and response.endswith("```"):
            response = response[3:-3]
        elif response.startswith("`") and response.endswith("`"):
            response = response[1:-1]

        return response
    def add_system_prompt(self, str):
        self.SYSTEM_PROMPT = self.SYSTEM_PROMPT + str
