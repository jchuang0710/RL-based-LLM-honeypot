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

# 記得金鑰不要洩漏出去
api_key = os.environ['OPENAI_API_KEY']
client = OpenAI(api_key = api_key)

path = '/home/atomics'
dirPath = '/workspace/LLM-Honeypot/atomic-red-team/atomics/T*/*.yaml'
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
total = 0
correct = 0
i=0
for f in file_set:
    yaml_dict = load_yaml(f)
    flag = False
    for item in yaml_dict['atomic_tests']:
        command_set = []
        if 'linux' in item['supported_platforms']:
            set1.add(yaml_dict['attack_technique'])
            print(yaml_dict['attack_technique'])
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
            
            #message_history = [{"role": "system", "content": "I want you to act as a ubuntu terminal which have join into ad domain 'hslab.com' which contain ten domain computer and 20 domain user.Please set the relevant parameters randomly.  I will type commands and you will reply with what the terminal should show. I want you only to reply with the terminal output in plaintest, and nothing else.You have already install all atomic red team relatvie file under path '/home/atomic'. Some commands will be composed of multiple instructs, please reply them in order and reply need to consider the previous instructs.  Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output. All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets {like this}."}]
            message_history = [{"role": "system", "content": "I want you to act as a ubuntu terminal. Please set the relevant parameters randomly.  I will type commands and you will reply with what the terminal should show. I want you only to reply with the terminal output in plaintest, and nothing else.You have already install all atomic red team relatvie file under path '/home/atomic'. Some commands will be composed of multiple instructs, please reply them in order and reply need to consider the previous instructs.  Do not write explanations. Do not type commands unless I instruct you to do so. Don't omit any output. All the software have already install. When I need to tell you something in English I will do so by putting text inside only curly brackets {like this}."}]
            for command in command_set:
                message_history.append({"role": "user", "content": command})
                outputs = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=message_history
                )
                response = outputs.choices[0].message.content

                if response.startswith("plaintext"):
                    response = response[9:0]
                elif response.startswith("```") and response.endswith("```"):
                    response = response[3:-3]
                elif response.startswith("`") and response.endswith("`"):
                    response = response[1:-1]
                
                message_history.append({"role": "assistant", "content": response})
            '''
            
            # Cowrie generate command/response pair
            
            # 建立一个sshclient对象
            #paramiko.common.logging.basicConfig(level=paramiko.common.DEBUG)
            ssh = paramiko.SSHClient()
            # 允许将信任的主机自动加入到host_allow 列表，此方法必须放在connect方法的前面
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # 调用connect方法连接服务器
            ssh.connect(hostname='192.168.101.26', port=22, username='test', password='test')
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
                        history = history + '\ninput:' + item['content']
                    else:
                        #print('content:', item)
                        history = history + '\noutput:' + item['content']
                i = i + 1
            
            Completion = client.chat.completions.create( 
                model="gpt-4o",
                messages=[ 
                    #{ "role" : "system" , "content" : "The following is some system input and output please determine the attack is success or not, and system is honeypot or not. If attack is success and system is not honeypot please reply yes, else reply no. don't explain."},
                    { "role" : "system" , "content" : "The following is some system input and output please determine the system is honeypot or not. If system is not honeypot please reply yes, else reply no. don't explain."},
                    { "role" : "user" , "content" : history}
                ] 
            ) 
            print ('Analysis honeypot or not: ', Completion.choices[0].message.content)
            total = total + 1
            if (Completion.choices[0].message.content == 'yes'):
                correct = correct + 1
            
            #print('history:', history)
            print('total:', total, 'success: ', correct, ' f1-score: ', correct/total)
            #input('next')

path = 'output.txt'
with open(path, 'w') as f:
    f.write('total:' + str(total) + 'success: ' + str(correct) + ' f1-score: ' + str(correct/total))
print('end')