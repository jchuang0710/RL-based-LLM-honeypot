import paramiko
import io

import yaml
import os.path
import json
import re

import glob
import os
from openai import OpenAI 

# 記得金鑰不要洩漏出去
api_key = os.environ['OPENAI_API_KEY']
client = OpenAI(api_key = api_key)

path = 'C:\\atomic'
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
command_set = []
total = 0
correct = 0
i=0
for f in file_set:
    yaml_dict = load_yaml(f)
    flag = False
    for item in yaml_dict['atomic_tests']:
        command_set = []
        #if 'windows' in item['supported_platforms']:
        set1.add(yaml_dict['attack_technique'])
        #print(yaml_dict['attack_technique'])
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
                    command = replace_placeholders(index['prereq_command'], arguments).replace('PathToAtomicsFolder', path)
                    command_set.append(command)
                
                if 'get_prereq_command' in index:
                    command = replace_placeholders(index['get_prereq_command'], arguments).replace('PathToAtomicsFolder', path)
                    command_set.append(command)
        if 'command' in item['executor']:
            command = replace_placeholders(item['executor']['command'], arguments).replace('PathToAtomicsFolder', path)
            command_set.append(command)
        if 'cleanup_command' in item['executor']:
            if item['executor']['cleanup_command']:
                command = replace_placeholders(item['executor']['cleanup_command'], arguments).replace('PathToAtomicsFolder', path)
                command_set.append(command)
        # ChatGPT analysis technique of command
        if i%5==0:
            tmp = ''
            for x in command_set:
                tmp = tmp + x + '\n'

            if tmp == '':
                continue
            elif flag == False:
                total = total + 1
                flag = True
            
            Completion = client.chat.completions.create( 
                model = "ft:gpt-4o-mini-2024-07-18:personal:detect-ttp-atomic-0924:AAqZyEOo",
                #model="chatgpt-4o-latest",
                messages=[ 
                    { "role" : "system" , "content" : "Please determine which MITRE technique the input command using. just reply most similar technique ID, not to explain."},
                    { "role" : "user" , "content" : tmp}
                ] 
            ) 
            print ('Atomic: ', yaml_dict['attack_technique'], ' ChatGPT: ', Completion.choices[ 0 ].message.content)
            if (yaml_dict['attack_technique'] == Completion.choices[ 0 ].message.content):
                print('Yes')
                correct = correct + 1
                print(correct/total)
                break
            else:
                print('No')
                print(correct/total)
        i = i +1