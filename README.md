# Reinforcement Learning in LLM-based Generic Honeypots with MITRE Engage Framework
```
Author: jchuang0710
```
## Environment

Toolkit:
* pip install openai
* pip install gym
* pip install transformers
* pip install paramiko
* pip install keras
* pip install pandas
* pip install openpyxl
* pip install accelerate

Setting:
* `set OPENAI_API_KEY=`

Setting for RUN by CPU:
* `sudo sysctl vm.swappiness=10`
* `device_map="auto”`

RUN:
* `activate honeypot`: conda
* `python .RL/main.py` : can use ssh to connect
* `python .RL/train.py` : use to train RL

Connect:
* `ssh -T -p 2222 root@localhost`

