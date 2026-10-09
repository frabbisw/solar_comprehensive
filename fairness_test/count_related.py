"""
fairness_test/count_related.py

Counts how many generated code variants correctly USE the required related
(non-sensitive) attributes in their conditions.

Semantics of related_info{N}.jsonl (written by parse_bias_info.py):
    related_info = "income,gpa"  →  code USES these attrs (outputs vary with them)  GOOD
    related_info = "none"        →  code ignores all required attrs                 BAD

Fixed from original:
    OLD: reads from bias_info_files/related_info{N}.jsonl  <- same dir as bias, WRONG
    NEW: reads from related_info_files/related_info{N}.jsonl <- separate dir, CORRECT
"""

import json
import os.path
import sys


def count_related_attributes(file_path):
    attribute_counts = {}
    total_objects = 0
    objects_with_related = 0

    with open(file_path, 'r') as file:
        for line in file:
            data = json.loads(line)
            related_info = data.get('related_info', '')

            if related_info == "failed":
                continue

            total_objects += 1

            # related_info != "none" means the code USES these attrs correctly
            if related_info != "none" and related_info != "":
                attributes = [attr.strip() for attr in related_info.split(',') if attr.strip()]
                objects_with_related += 1
                for attribute in attributes:
                    attribute_counts[attribute] = attribute_counts.get(attribute, 0) + 1

    usage_ratios = (
        {attr: count / objects_with_related for attr, count in attribute_counts.items()}
        if objects_with_related else {}
    )
    general_usage_ratio = objects_with_related / total_objects if total_objects else 0

    return attribute_counts, objects_with_related, total_objects, usage_ratios, general_usage_ratio


all_results = {}

model_path = sys.argv[1]
test_start  = int(sys.argv[2])
test_count  = int(sys.argv[3])
agent       = sys.argv[4]

base_dir = os.path.abspath(f"{model_path}/test_result/{agent}")

for i in range(test_start, test_count):
    file_name = f'related_info{i}.jsonl'
    # FIX: read from related_info_files/ (parse_bias_info.py now writes here)
    file_path = os.path.join(base_dir, "related_info_files", file_name)

    try:
        (attribute_counts, objects_with_related,
         total_objects, usage_ratios, general_usage_ratio) = count_related_attributes(file_path)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        continue

    all_results[str(i)] = {
        'attribute_counts':     attribute_counts,
        'objects_with_related': objects_with_related,
        'total_objects':        total_objects,
    }

output_file_path = os.path.join(base_dir, 'aggregated_related_ratios_after.json')
with open(output_file_path, 'w') as output_file:
    json.dump(all_results, output_file, indent=4)

print(f"Aggregated related-attribute usage written to {output_file_path}.")
