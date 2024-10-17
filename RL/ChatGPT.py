from openai import OpenAI 
import os

api_key = os.environ['OPENAI_API_KEY']

class ChatGPT:
    def __init__(self, model_name="gpt-4o-mini"):
        # Model configuration
        self.BASE_MODEL_NAME = model_name
        self.SYSTEM_PROMPT = "I want you to act as a ubuntu terminal which have join into ad domain 'hslab.com' which contain ten domain computer and 20 domain user.Please set the relevant parameters randomly.  I will type commands and you will reply with what the terminal should show. I want you only to reply with the terminal output in plaintest, and nothing else.You have already install all atomic red team relatvie file under path '/home/atomic'. Some commands will be composed of multiple instructs, please reply them in order and reply need to consider the previous instructs.  Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output. All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets {like this}."
        
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
        tmp = action
        if type(query) == 'list':
            for item in query:
                tmp = tmp + item
        else:
            tmp = action + query
        #print(tmp)
        user_prompt = message_history + [{"role": "user", "content": tmp}]
        #print(message_history)
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
        message = "According to the system input and output detect the system is honeypot or not,just reply yes or no, don't explain why.\n"
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message = message + "input: "+ item + "\n"
                else:
                    message = message + "output: "+ item + "\n"

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
        
        message_history = [{"role": "system", "content": "Please analysis current state is in which MITRE tactic ID when I input current command. Tactic ID like TA0001, TA0002, ... ,TA0040. Please reply in this format 'Tactic ID: TA0001', don't explain why and don't reply anything else."}]
        message = "Please analysis current state is in which MITRE tactic ID when I input current command. Tactic ID like TA0001, TA0002, ... ,TA0040. Please reply in this format 'Tactic ID: TA0001', don't explain why and don't reply anything else.\n"
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message = message + "past_input: "+ item + "\n"

        #message.append("current input: "+ query + "\n")
        #print(query)
        tmp = ""
        if type(query) == 'list':
            for item in query:
                tmp = tmp + item
        else:
            tmp = query
        #print(type(tmp))
        tmp = message + "current command: "+ str(tmp) + "\n"
        user_prompt = [{"role": "user", "content": tmp}] 
        
        outputs = self.llm.chat.completions.create( 
            model=self.BASE_MODEL_NAME,
            messages=user_prompt
        ) 

        response = outputs.choices[0].message.content
        #print(response)
        return self.translate_tactic_id(response)

    def translate_tactic_id(self, response):
        response = response[-6:]
        if 'TA0001' == response:
            return 1
        elif 'TA0002' == response:
            return 2
        elif 'TA0003' == response:
            return 3
        elif 'TA0004' == response:
            return 4
        elif 'TA0005' == response:
            return 5
        elif 'TA0006' == response:
            return 6
        elif 'TA0007' == response:
            return 7
        elif 'TA0008' == response:
            return 8
        elif 'TA0009' == response:
            return 9
        elif 'TA0011' == response:
            return 10
        elif 'TA0010' == response:
            return 11
        elif 'TA0040' == response:
            return 12
        else:
            return 1

