# Reinforcement Learning in LLM-based Generic Honeypots with MITRE Engage Framework
```
Author: jchuang0710
```
## Environment
Base Image: 
* pytorch/pytorch

Toolkit:
* `pip install -r requirements.txt`

Setting:
* `export OPENAI_API_KEY=`

Setting for RUN by CPU:
* `sudo sysctl vm.swappiness=10`
* `device_map="auto”`

RUN:
* `python main.py` : open ssh port to network

Connect:
* `ssh -T -p 2222 root@localhost`

訓練與評估 RL: under RL
* `python train_by_LLM.py` : train RL model
* `python LLM_Evaluate_by_LLM.py`: evaluate model

評估 backend
* `python analysis_env.py` : 評估 honeypot backend 的好壞
