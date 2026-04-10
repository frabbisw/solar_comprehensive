import csv
import json

# File paths
jsonl_file_path = 'prompts.jsonl'
csv_file_path = 'prompts.csv'

# Read JSONL and write to CSV
with open(jsonl_file_path, mode='r', encoding='utf-8') as jsonl_file, \
        open(csv_file_path, mode='w', encoding='utf-8', newline='') as csv_file:
    # Read the first JSON object to get the CSV headers
    first_line = jsonl_file.readline()
    first_obj = json.loads(first_line)
    fieldnames = first_obj.keys()

    # Initialize the CSV writer
    csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

    # Write the header row to the CSV file
    csv_writer.writeheader()

    # Write the first row (since we've already read it)
    csv_writer.writerow(first_obj)

    # Iterate over the remaining lines in the JSONL file
    for line in jsonl_file:
        json_obj = json.loads(line)
        csv_writer.writerow(json_obj)

print(f"JSONL data has been successfully converted to CSV and saved to {csv_file_path}")
