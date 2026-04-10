import csv
import json

# File paths
csv_file_path = 'prompts_32.csv'
jsonl_file_path = 'prompts_32.jsonl'

# Reading CSV and writing to JSONL
with open(csv_file_path, mode='r', encoding='utf-8') as csv_file, \
        open(jsonl_file_path, mode='w', encoding='utf-8') as jsonl_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        # Convert the row to a JSON string
        json_string = json.dumps(row)
        # Write to JSONL file
        jsonl_file.write(json_string + '\n')

print(f"CSV data has been successfully converted to JSONL and saved to {jsonl_file_path}")
