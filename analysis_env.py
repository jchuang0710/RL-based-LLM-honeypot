import paramiko
import io

import yaml
import os.path
import json
import re

import glob
import os
from openai import OpenAI 

import paramiko
import time

env = 'linux' #108
# env = 'windows' #257

# 記得金鑰不要洩漏出去
api_key = os.environ['OPENAI_API_KEY']
client = OpenAI(api_key = api_key)

if env == 'linux':
    path = '/home/atomics'
if env == 'windows':
    path = 'C:\\atomics'
dirPath = 'C:\\Users\\User\\Documents\\GitHub\\RL-based-LLM-honeypot\\atomic-red-team\\atomics\\T*\\*.yaml'
file_set = glob.glob(dirPath)
file_set.sort()

def replace_placeholders(data, input_arguments):
    # 使用正則表達式匹配 #{VAR_NAME} 的樣式
    pattern = re.compile(r'#\{(\w+)\}')
    
    if isinstance(data, dict):
        return {k: replace_placeholders(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_placeholders(v) for v in data]
    elif isinstance(data, str):
        return pattern.sub(lambda match: input_arguments.get(match.group(1), match.group(0)), data)
    else:
        return data

def load_yaml(file_name):
    """Load YAML file to be dict"""
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding="utf-8") as fr:
            dict_obj = yaml.load(fr, Loader=yaml.FullLoader)
        return dict_obj
    else:
        raise FileNotFoundError('NOT Found YAML file %s' % file_name)
set1 = set()
total = 1
correct = 0
i=0
for f in file_set:
    yaml_dict = load_yaml(f)
    flag = False
    for item in yaml_dict['atomic_tests']:
        command_set = []
        if env in item['supported_platforms']:
            # print(yaml_dict['attack_technique'])
            set1.add(yaml_dict['attack_technique'])
            arguments = {}
            #flag = True
            if 'input_arguments' in item:
                for argument in item['input_arguments']:
                    if type(item['input_arguments'][argument]['default']) != str:
                        arguments[argument] = str(item['input_arguments'][argument]['default'])
                    else:
                        arguments[argument] = item['input_arguments'][argument]['default']
            if 'dependencies' in item:
                for index in item['dependencies']:
                    
                    if 'prereq_command' in index:
                        '''
                        command = replace_placeholders(index['prereq_command'], arguments).replace('PathToAtomicsFolder', path)
                        tmp = command.split('\n')
                        for i in tmp:
                            if i != '':
                                command_set.append(i)
                        '''
                    
                    if 'get_prereq_command' in index:
                        command = replace_placeholders(index['get_prereq_command'], arguments).replace('PathToAtomicsFolder', path)
                        tmp = command.split('\n')
                        for i in tmp:
                            if i != '':
                                command_set.append(i)
                        

            if 'command' in item['executor']:
                command = replace_placeholders(item['executor']['command'], arguments).replace('PathToAtomicsFolder', path)
                tmp = command.split('\n')
                for i in tmp:
                    if i != '':
                        command_set.append(i)
                
                
            
            if 'cleanup_command' in item['executor']:
                '''
                command = replace_placeholders(item['executor']['cleanup_command'], arguments).replace('PathToAtomicsFolder', path)
                tmp = command.split('\n')
                for i in tmp:
                    if i != '':
                        command_set.append(i)
                '''
            '''
            # ChatGPT generate command/response pair
            if env == 'linux':
                message_history = [{"role": "system", "content": "I want you to act as a ubuntu terminal. Please set the relevant parameters randomly.  I will type commands and you will reply with what the terminal should show. I want you only to reply with the terminal output in plaintest, and nothing else.You have already install all atomic red team relatvie file under path '/home/atomic'. Some commands will be composed of multiple instructs, please reply them in order and reply need to consider the previous instructs.  Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output. All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets {like this}."}]
            if env == 'windows':
                message_history = [{"role": "system", "content": "I want you to act as a windows powershell which have join into ad domain 'hslab.com' which contain ten domain computer and 20 domain user.Please set the relevant parameters randomly.  I will type commands and you will reply with what the powershell should show. I want you only to reply with the powershell output in plaintest, and nothing else.You have already install all atomic red team relative file under path 'C:\\atomics'. Some commands will be composed of multiple instructs, please reply them in order and reply need to consider the previous instructs.  Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output. All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets {like this}."}]
            try:
                for command in command_set:
                    message_history.append({"role": "user", "content": command})
                    outputs = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=message_history
                    )
                    response = outputs.choices[0].message.content
                    response.replace("plaintext", '')
                    if response.startswith("plaintext"):
                        response = response[9:0]
                    elif response.startswith("```") and response.endswith("```"):
                        response = response[3:-3]
                    elif response.startswith("`") and response.endswith("`"):
                        response = response[1:-1]
                    
                    message_history.append({"role": "assistant", "content": response})
            except:
                continue
            '''
            '''
            # Cowrie generate command/response pair
            
            # 建立一个sshclient对象
            #paramiko.common.logging.basicConfig(level=paramiko.common.DEBUG)
            ssh = paramiko.SSHClient()
            # 允许将信任的主机自动加入到host_allow 列表，此方法必须放在connect方法的前面
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # 调用connect方法连接服务器
            # Linux
            if env == 'linux':
                ssh.connect(hostname='192.168.101.26', port=22, username='test', password='test')
            # Windows
            if env == 'windows':
                ssh.connect(hostname='192.168.101.23', port=22, username='TEST/Administrator', password='Win*Server')
            # 执行命令
            shell = ssh.invoke_shell()
            time.sleep(0.1)
            output = shell.recv(65535).decode()
            message_history = []
            try:
                for command in command_set:
                    shell.send(command + '\n')
                    time.sleep(0.1)
                    output = shell.recv(65535).decode()

                    output = output.replace(command, '')

                    message_history.append({"role": "user", "content": command})
                    message_history.append({"role": "assistant", "content": output})
                    #print('command:', command)
                    #print('output:', output)
            except:
                continue
            finally:
                # 关闭连接
                ssh.close()
            '''
            '''
            # ChatGPT judge the env is real or not
            history = ''
            i = 0
            for item in message_history:
                if i == 0:
                    i = i + 1
                    continue
                else:
                    if i%2 == 0 :
                        #print('content:', item)
                        history = history + '\noutput:' + item['content']
                        with open('{}_gpt.txt'.format(env), 'a') as f:
                            f.write('output: ' + item['content']+'\n')
                    else:
                        #print('content:', item)
                        history = history + '\ninput:' + item['content']
                        with open('{}_gpt.txt'.format(env), 'a') as f:
                            f.write('input: ' + item['content']+'\n')
                i = i + 1
            try:
                Completion = client.chat.completions.create( 
                    model="gpt-4o",
                    messages=[ 
                        # { "role" : "system" , "content" : "The following is some system input and output please determine the attack is success or not, and system is honeypot or not. If attack is success and system is not honeypot please reply yes, else reply no. don't explain."},
                        { "role" : "system" , "content" : "According to the system input and output detect the system is honeypot or not,just reply yes or no, don't explain why."},
                        { "role" : "user" , "content" : history}
                    ] 
                )
            except:
                continue
            with open('{}_gpt.txt'.format(env), 'a') as f:
                f.write('Analysis honeypot or not: '+ Completion.choices[0].message.content+'\n\n') 
            print ('Analysis honeypot or not: ', Completion.choices[0].message.content)
            total = total + 1
            if (Completion.choices[0].message.content == 'yes' or Completion.choices[0].message.content == 'Yes'):
                correct = correct + 1
                set1.add(yaml_dict['attack_technique'])
            
            #print('history:', history)
            print('total:', total, 'success: ', correct, ' Simulate Success Rate: ', correct/total)
            #input('next')
            '''
print(set1)
print(len(set1))
techniqueID = ['T1001.002', 'T1003.007', 'T1003.008', 'T1005', 'T1007', 'T1014', 'T1016.001', 'T1016', 'T1018', 'T1021.004', 'T1027.001', 'T1027.002', 'T1027.004', 'T1027', 'T1030', 'T1033', 'T1036.003', 'T1036.004', 'T1036.005', 'T1036.006', 'T1037.004', 'T1040', 'T1046', 'T1048.002', 'T1048.003', 'T1048', 'T1049', 'T1053.002', 'T1053.003', 'T1053.006', 'T1056.001', 'T1057', 'T1059.004', 'T1059.006', 'T1069.001', 'T1069.002', 'T1070.002', 'T1070.003', 'T1070.004', 'T1070.006', 'T1070.008', 'T1071.001', 'T1074.001', 'T1078.003', 'T1082', 'T1083', 'T1087.001', 'T1087.002', 'T1090.001', 'T1090.003', 'T1098.004', 'T1105', 'T1110.001', 'T1110.004', 'T1113', 'T1115', 'T1124', 'T1132.001', 'T1135', 'T1136.001', 'T1136.002', 'T1140 T1201', 'T1217', 'T1222.002', 'T1485', 'T1486', 'T1489', 'T1496', 'T1497.001', 'T1497.003', 'T1518.001', 'T1529', 'T1531', 'T1543.002', 'T1546.004', 'T1546.005', 'T1547.006', 'T1548.001', 'T1548.003', 'T1552.001', 'T1552.003', 'T1552.004', 'T1552.007', 'T1552', 'T1553.004', 'T1555.003', 'T1556.003', 'T1560.001', 'T1560.002', 'T1562.001', 'T1562.003', 'T1562.004', 'T1562.006', 'T1562.008', 'T1562.010', 'T1562.012', 'T1562', 'T1564.001', 'T1569.002', 'T1571', 'T1574.006', 'T1580', 'T1614.001', 'T1614']
print(len(techniqueID))
techniqueID = ['T1652', 'T1037.001', 'T1136.002', 'T1486', 'T1137', 'T1553.003', 'T1187', 'T1010', 'T1574.011', 'T1218.005', 'T1069.002', 'T1119', 'T1110.002', 'T1201', 'T1036.003', 'T1087.002', 'T1091', 'T1018', 'T1220', 'T1546.008', 'T1557.001', 'T1572', 'T1055.012', 'T1095', 'T1110.004', 'T1040', 'T1003.003', 'T1055.004', 'T1546.011', 'T1222.001', 'T1127.001', 'T1574.002', 'T1027.007', 'T1505.005', 'T1560', 'T1543.003', 'T1072', 'T1053.002', 'T1059.003', 'T1078.003', 'T1090.001', 'T1558.002', 'T1134.004', 'T1114.001', 'T1547.012', 'T1120', 'T1055.011', 'T1547.009', 'T1547.002', 'T1134.001', 'T1090.003', 'T1558.001', 'T1003.004', 'T1112', 'T1574.001', 'T1020', 'T1564', 'T1055.015', 'T1007', 'T1137.004', 'T1222', 'T1574.012', 'T1560.001', 'T1071', 'T1016.001', 'T1059.005', 'T1218.004', 'T1137.006', 'T1562.002', 'T1070.003', 'T1033', 'T1567.003', 'T1573', 'T1055.001', 'T1484.001', 'T1012', 'T1195', 'T1001.002', 'T1489', 'T1070', 'T1071.001', 'T1547.001', 'T1556.002', 'T1567.002', 'T1003.006', 'T1529', 'T1218.011', 'T1005', 'T1106', 'T1482', 'T1552.002', 'T1654', 'T1197', 'T1016', 'T1127', 'T1123', 'T1218.009', 'T1542.001', 'T1559', 'T1563.002', 'T1539', 'T1622', 'T1552.001', 'T1218.003', 'T1497.001', 'T1217', 'T1491.001', 'T1110.003', 'T1547', 'T1574.008', 'T1574.009', 'T1059', 'T1069.001', 'T1546.013', 'T1615', 'T1137.001', 'T1555.003', 'T1559.002', 'T1553.006', 'T1564.003', 'T1070.005', 'T1546.009', 'T1649', 'T1048.002', 'T1569.002', 'T1562.004', 'T1505.003', 'T1027.006', 'T1547.015', 'T1550.002', 'T1055', 'T1553.005', 'T1614', 'T1087.001', 'T1219', 'T1547.003', 'T1553.004', 'T1592.001', 'T1132.001', 'T1113', 'T1027', 'T1057', 'T1218.002', 'T1555.004', 'T1027.004', 'T1485', 'T1564.002', 'T1571', 'T1218.008', 'T1562.001', 'T1036.005', 'T1546.015', 'T1021.003', 'T1082', 'T1030', 'T1055.002', 'T1176', 'T1124', 'T1056.001', 'T1137.002', 'T1552.006', 'T1550.003', 'T1555', 'T1021.002', 'T1083', 'T1546.001', 'T1021.001', 'T1202', 'T1049', 'T1048', 'T1566.001', 'T1216', 'T1564.004', 'T1078.001', 'T1070.001', 'T1136.001', 'T1216.001', 'T1548.002', 'T1204.003', 'T1125', 'T1046', 'T1021.006', 'T1059.007', 'T1620', 'T1614.001', 'T1003.002', 'T1221', 'T1546.010', 'T1218', 'T1039', 'T1547.004', 'T1558.004', 'T1547.008', 'T1134.002', 'T1558.003', 'T1041', 'T1003.001', 'T1564.001', 'T1505.004', 'T1547.006', 'T1129', 'T1218.007', 'T1562', 'T1546', 'T1070.008', 'T1531', 'T1552', 'T1070.006', 'T1006', 'T1490', 'T1546.007', 'T1570', 'T1048.003', 'T1552.004', 'T1135', 'T1003.005', 'T1110.001', 'T1204.002', 'T1207', 'T1505.002', 'T1546.002', 'T1218.001', 'T1562.003', 'T1134.005', 'T1036', 'T1056.004', 'T1016.002', 'T1518']
print(len(techniqueID))
path = 'output.txt'
with open(path, 'w') as f:
    f.write('total:' + str(total) + 'success: ' + str(correct) + ' Simulate Success Rate: ' + str(correct/total))
print('end')
