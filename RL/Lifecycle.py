
import yaml
import os.path
import json
import re
import pandas as pd
import glob
import random
import setting
if setting.mode == 'train':
    random.seed(10) # train.py
elif setting.mode == 'test':
    random.seed(11) # evaluate.py

atomic_path = '../atomic-red-team/atomics/T*/*.yaml'
if setting.system == 'linux':
    victim_path = '/home/atomics'
elif setting.system == 'windows':
    victim_path = 'C:\\atomics'
lifecycle_path = "lifecycle.xlsx"

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

# 取得 ART 所有的 technique command mapping
def get_technique_command():
    path = victim_path
    dirPath = atomic_path
    file_set = glob.glob(dirPath)
    file_set.sort()

    command_set = ""
    total = 0
    correct = 0
    i=0
    technique_command = {}
    for f in file_set:
        yaml_dict = load_yaml(f)
        flag = False
        for item in yaml_dict['atomic_tests']:
            command_set = []
            if yaml_dict['attack_technique'] not in technique_command:
                technique_command[yaml_dict['attack_technique']] = []
                #print('add:',yaml_dict['attack_technique'])
            if setting.system in item['supported_platforms']:
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
                        
                        '''
                        if 'prereq_command' in index:
                            command = replace_placeholders(index['prereq_command'], arguments).replace('PathToAtomicsFolder', path)
                            command_set.append(command)
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
                    #command_set.append(command)

                '''
                if 'cleanup_command' in item['executor']:
                    if item['executor']['cleanup_command']:
                        command = replace_placeholders(item['executor']['cleanup_command'], arguments).replace('PathToAtomicsFolder', path)
                        command_set.append(command)
                '''
            if command_set != []:
                technique_command[yaml_dict['attack_technique']].append(command_set)
    
    return technique_command
            
# 從 execl 中取出所有的 lifecycle
def get_lifecycle():
    
    df=pd.read_excel(lifecycle_path)

    # 轉成 numpy.ndarray 格式
    nmp=df.values
    lifecycle = {}
    for item in nmp:
        if item[0] not in lifecycle:
            lifecycle[item[0]] = []
        lifecycle[item[0]].append(item[1])

    return lifecycle

# 隨機取得一個 lifecycle 所使用的 command
def get_lifecycle_command():
    # 取得所有的 lifecycle
    lifecycle_set = get_lifecycle()
    # 取得所有的 technique 所使用的 procedure
    technique_command = get_technique_command()
    lifecycle_command = []
    #print(technique_command)
    # 隨機選一個 lifecycle
    for technique in lifecycle_set[random.choice(list(lifecycle_set.keys()))]:
        
        if technique in technique_command and technique_command[technique] != []:
            # 隨機選一個 procedure
            for command in random.choice(technique_command[technique]):
                #print(command)
                lifecycle_command.append(command)
    return lifecycle_command

# 取得一個 technique 所使用的 command
def get_command(technique):
    technique_command = get_technique_command()
    next_command_set = []
    # 隨機選一個 procedure
    for command in random.choice(technique_command[technique]):
        #print(command)
        next_command_set.append(command)
    
    return next_command_set

def technique_exist(technique):
    technique_command = get_technique_command()
    if technique in technique_command and technique_command[technique] != []:
        return True
    return False