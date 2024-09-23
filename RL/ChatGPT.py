from openai import OpenAI 
import os

api_key = os.environ['OPENAI_API_KEY']

class ChatGPT:
    def __init__(self, model_name="gpt-4o-mini"):
        # Model configuration
        self.BASE_MODEL_NAME = model_name
        self.SYSTEM_PROMPT = "I want you to act as a ubuntu terminal which have join into ad domain 'hslab.com'.Please set the relevant parameters randomly.  I will type commands and you will reply with what the terminal should show. I want you only to reply with the terminal output in plaintest, and nothing else. Some commands will be composed of multiple instructs, please reply them in order and reply need to consider the previous instructs.  Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output. All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets {like this}. You should print the terminal output first, final line is the prompt for input, the prompt should follow this format 'user-name@computer-name:curr-dir$ '."
        
        # 記得金鑰不要洩漏出去
        self.llm = OpenAI(api_key = api_key)

        print("Loaded Model: ", self.BASE_MODEL_NAME)

    def answer(self, action, query, log_history=[], max_tokens=4096, temperature=0.01, top_p=0.8):

        message_history = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message_history.append({"role": "user", "content": item})
                else:
                    message_history.append({"role": "assistant", "content": item})

        user_prompt = message_history + [{"role": "user", "content": action + query}]
        
        outputs = self.llm.chat.completions.create( 
            model=self.BASE_MODEL_NAME,
            messages=user_prompt
        ) 

        response = outputs.choices[0].message.content
        
        # remove unnecessary quotes
        if response.startswith("plaintext"):
            response = response[9:0]
        elif response.startswith("```") and response.endswith("```"):
            response = response[3:-3]
        elif response.startswith("`") and response.endswith("`"):
            response = response[1:-1]

        return response
    
    def add_system_prompt(self, str):
        self.SYSTEM_PROMPT = self.SYSTEM_PROMPT + str

    def detect_honeypot(self, log_history=[], max_tokens=4096, temperature=0.01, top_p=0.8):

        message_history = [{"role": "system", "content": "According to the system input and output detect the system is honeypot or not,just reply yes or no, don't explain why."}]
        
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message.append("input: "+ item + "\n")
                else:
                    message.append("output: "+ item + "\n")

        user_prompt = message_history + [{"role": "user", "content": message}]
        
        outputs = self.llm.chat.completions.create( 
            model=self.BASE_MODEL_NAME,
            messages=user_prompt
        ) 

        response = outputs.choices[0].message.content
        
        if response == "yes":
            return True

        return False

    def next_state(self, action, query, log_history=[], max_tokens=4096, temperature=0.01, top_p=0.8):
        
        message_history = [{"role": "system", "content": "Please analysis current tactic state about current input ,just tactic ID, don't explain why."}]
        
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message.append("past_input: "+ item + "\n")

        message.append("current input: "+ query + "\n")
        user_prompt = message_history + [{"role": "user", "content": message}]
        
        outputs = self.llm.chat.completions.create( 
            model=self.BASE_MODEL_NAME,
            messages=user_prompt
        ) 

        response = outputs.choices[0].message.content

        return response