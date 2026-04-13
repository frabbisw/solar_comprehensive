import json

from pyparsing import line

cnt = 0
s = 0

def count_bias_info(file):
    with open(file, 'r') as f:
        data = json.loads(f.read())
        bias_info = data.get('bias_info', "none")
    return bias_info
        

for i in range(30):
    dev = f"/home/f_rabbi/solar_comprehensive/results/gpt35/test_result/developer/bias_info_files/bias_info{i}.jsonl"
    
    round1 = f"/home/f_rabbi/solar_comprehensive/results/gpt35/test_result/repairer_round1/bias_info_files/bias_info{i}.jsonl"
    round2 = f"/home/f_rabbi/solar_comprehensive/results/gpt35/test_result/repairer_round2/bias_info_files/bias_info{i}.jsonl"
    round3 = f"/home/f_rabbi/solar_comprehensive/results/gpt35/test_result/repairer_round3/bias_info_files/bias_info{i}.jsonl"

    bias_info_dev = count_bias_info(dev)
    bias_info_round1 = count_bias_info(round1)
    bias_info_round2 = count_bias_info(round2)
    bias_info_round3 = count_bias_info(round3)

    if bias_info_round2 == "none" and bias_info_round3 != "none":
        print(f"Index: {i}, Round 2: {bias_info_round1}, Round 3: {bias_info_round2}")