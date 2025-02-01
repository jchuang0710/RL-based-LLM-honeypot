from openai import OpenAI 
import os
import time
api_key = os.environ['OPENAI_API_KEY']

class ChatGPT:
    def __init__(self, model_name="gpt-4o-mini"):
        # Model configuration
        self.BASE_MODEL_NAME = model_name
        #self.SYSTEM_PROMPT = "I want you to act as a ubuntu terminal which have join into ad domain 'hslab.com' which contain ten domain computer and 20 domain user.Please set the relevant parameters randomly.  I will type commands and you will reply with what the terminal should show. I want you only to reply with the terminal output in plaintest, and nothing else.You have already install all atomic red team relatvie file under path '/home/atomic'. Some commands will be composed of multiple instructs, please reply them in order and reply need to consider the previous instructs.  Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output. All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets {like this}."
        
        self.SYSTEM_PROMPT = f"""
            I want you to act as a ubuntu terminal which have join into ad domain 'hslab.com'.
            I will type commands and you will reply with what the terminal should show.
            I want you only to reply with the terminal output in plaintest, and nothing else.
            You should not generate any instruction from {{}}, only response the system output from which command outside the {{}}.
            Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output.
            All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets.
            You should print the terminal output first, final is the prompt for input like this 'user-name@computer-name:curr-dir$ '.
            """
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

    def detect_honeypot2(self, log_history=[], max_tokens=4096, temperature=0.01, top_p=0.8):

        message_history = [{"role": "system", "content": "According to the system input and output detect the system is honeypot or not,just reply yes or no, don't explain why."}]
        #message = "According to the system input and output detect the system is honeypot or not,just reply yes or no, don't explain why.\n"
        message = ""
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

    def detect_next_state(self, action, query, log_history=[], max_tokens=4096, temperature=0.01, top_p=0.8):
        
        message = "Please analysis current state is in which MITRE tactic and technique when I input current command. Tactic ID like TA0001, TA0002, ... ,TA0040. Technique ID like T1001, T1002, ... ,T1485. Please just reply Tactic ID first and then Technique ID like 'TA0001 T1485', don't explain and don't reply anything else and don't reply sub-technique like T1001.001. just reply in this format 'TA0001 T1001'\n"
        message_history = [{"role": "system", "content": message}]
        message = ""
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message = message + "past_input: "+ item + "\n"

        tmp = message + "current command: "+ str(query) + "\n"
        message_history.append({"role": "user", "content": tmp})
        user_prompt = [{"role": "user", "content": tmp}] 
        
        response = []
        while len(response) < 2:
            try:
                outputs = self.llm.chat.completions.create( 
                    model="ft:gpt-4o-mini-2024-07-18:personal:detect-ttp-atomic-0924:AAqZyEOo",
                    messages=user_prompt
                ) 

                response = outputs.choices[0].message.content
                response = response.split(' ')
            except:
                print('sleep 20s')
                time.sleep(20)
                continue

        return self.translate_tactic_id(response[0]), self.translate_technique_id(response[1])

    def translate_tactic_id(self, tactic):
        tacticID = ['TA0001','TA0002', 'TA0003', 'TA0004', 'TA0005', 'TA0006', 'TA0007', 'TA0008', 'TA0009', 'TA0011', 'TA0010', 'TA0040']
        print(tactic)
        if tactic in tacticID:
            return tacticID.index(tactic)
        else:
            return 1
    
    def translate_technique_id(self, technique):
        if len(technique) > 5:
            technique = technique[:5]
        print(technique)
        techniqueID = ['T1548', 'T1134', 'T1531', 'T1087', 'T1098', 'T1650', 'T1583', 'T1595', 'T1557', 'T1071', 'T1010', 'T1560', 'T1123', 'T1119', 'T1020', 'T1197', 'T1547', 'T1037', 'T1176', 'T1217', 'T1185', 'T1110', 'T1612', 'T1115', 'T1651', 'T1580', 'T1538', 'T1526', 'T1619', 'T1059', 'T1092', 'T1586', 'T1554', 'T1584', 'T1609', 'T1613', 'T1659', 'T1136', 'T1543', 'T1555', 'T1485', 'T1132', 'T1486', 'T1530', 'T1602', 'T1213', 'T1005', 'T1039', 'T1025', 'T1565', 'T1001', 'T1074', 'T1030', 'T1622', 'T1491', 'T1140', 'T1610', 'T1587', 'T1652', 'T1006', 'T1561', 'T1484', 'T1482', 'T1189', 'T1568', 'T1114', 'T1573', 'T1499', 'T1611', 'T1585', 'T1546', 'T1480', 'T1048', 'T1041', 'T1011', 'T1052', 'T1567', 'T1190', 'T1203', 'T1212', 'T1211', 'T1068', 'T1210', 'T1133', 'T1008', 'T1083', 'T1222', 'T1657', 'T1495', 'T1187', 'T1606', 'T1592', 'T1589', 'T1590', 'T1591', 'T1615', 'T1200', 'T1564', 'T1665', 'T1574', 'T1562', 'T1656', 'T1525', 'T1070', 'T1202', 'T1105', 'T1490', 'T1056', 'T1559', 'T1534', 'T1570', 'T1654', 'T1036', 'T1556', 'T1578', 'T1112', 'T1601', 'T1111', 'T1621', 'T1104', 'T1106', 'T1599', 'T1498', 'T1046', 'T1135', 'T1040', 'T1095', 'T1571', 'T1027', 'T1588', 'T1137', 'T1003', 'T1201', 'T1120', 'T1069', 'T1566', 'T1598', 'T1647', 'T1653', 'T1542', 'T1057', 'T1055', 'T1572', 'T1090', 'T1012', 'T1620', 'T1219', 'T1563', 'T1021', 'T1018', 'T1091', 'T1496', 'T1207', 'T1014', 'T1053', 'T1029', 'T1113', 'T1597', 'T1596', 'T1593', 'T1594', 'T1505', 'T1648', 'T1489', 'T1129', 'T1072', 'T1518', 'T1608', 'T1528', 'T1649', 'T1558', 'T1539', 'T1553', 'T1195', 'T1218', 'T1082', 'T1614', 'T1016', 'T1049', 'T1033', 'T1216', 'T1007', 'T1569', 'T1529', 'T1124', 'T1080', 'T1221', 'T1205', 'T1537', 'T1127', 'T1199', 'T1552', 'T1535', 'T1550', 'T1204', 'T1078', 'T1125', 'T1497', 'T1600', 'T1102', 'T1047', 'T1220']
        if technique in techniqueID:
            return techniqueID.index(technique)
        else:
            return 1

