"""
fairness_test/parse_bias_info.py

Reads Solar test log CSVs and produces two sets of JSONL files:

  bias_info_files/bias_info{N}.jsonl
      {"variant": "1", "bias_info": "gender,race"}  or  {"variant": "1", "bias_info": "none"}
      Sensitive attributes whose variation caused inconsistent outputs (code is biased on these).

  related_info_files/related_info{N}.jsonl          ← FIX: separate directory
      {"variant": "1", "related_info": "income,gpa"} or {"variant": "1", "related_info": "none"}
      Related (non-sensitive) attributes that the code DOES use in conditions.
      "none" means the code ignores all required related attributes.

Semantics:
  For SENSITIVE attrs: "Inconsistencies found." = outputs differ when attr varies = BAD (bias)
  For RELATED attrs:   "Inconsistencies found." = outputs differ when attr varies = GOOD (attr is used)

Original bug fixed here:
  OLD: both bias_info and related_info written to bias_info_files/ (same dir)
  NEW: related_info written to related_info_files/ (separate dir)
  This allows bias_aware_reviewer.py to receive correct --bias_info_dir and --related_info_dir.

Usage:
  python parse_bias_info.py <log_dir> <bias_output_dir> <variant_num>
  e.g.:
  python parse_bias_info.py \
      results/gpt35/test_result/developer/log_files \
      results/gpt35/test_result/developer/bias_info_files \
      5
  → writes to bias_info_files/ and related_info_files/ (sibling of bias_info_files/)
"""

import json
import os
import re
import sys


def parse_line(line):
    """
    Parses a log line and extracts variant number, attribute name,
    whether inconsistencies were found, and whether it's a related attribute.

    Log line format:
      "Variant {N}, Sensitive_Attribute '{attr}':Inconsistencies found."
      "Variant {N}, Related_Attribute '{attr}':Inconsistencies found."
      "Variant {N}, Sensitive_Attribute '{attr}':No inconsistencies found."
    """
    parts = line.strip().split(':')
    variant_attribute = parts[0].strip()
    status = ':'.join(parts[1:]).strip()   # rejoin in case attr name contains ':'

    variant, attribute_with_prefix = variant_attribute.split(', ', 1)
    variant_number = variant.split(' ')[-1]
    attribute = re.search(r"Attribute '([^']+)'", attribute_with_prefix).group(1)
    has_inconsistencies = 'Inconsistencies found.' in status
    is_related = "Related" in attribute_with_prefix

    return variant_number, attribute, has_inconsistencies, is_related


def extract_number_from_filename(filepath):
    filename = filepath.split("/")[-1] if "/" in filepath else filepath
    match = re.search(r'(\d+)', filename)
    return match.group(0) if match else None


def process_file_to_jsonl(filepath, bias_output_dir, related_output_dir, max_variant_num):
    """
    Reads a log CSV file and writes:
      bias_output_dir/bias_info{N}.jsonl    — sensitive attrs that caused failures
      related_output_dir/related_info{N}.jsonl — related attrs that the code uses
    """
    number = extract_number_from_filename(filepath)
    if number is None:
        print(f"Could not extract number from filename {filepath}")
        return

    bias_jsonl_path    = os.path.join(bias_output_dir,    f"bias_info{number}.jsonl")
    related_jsonl_path = os.path.join(related_output_dir, f"related_info{number}.jsonl")

    variants = {str(i): {"sensitive_attributes": [], "related_attributes": []}
                for i in range(1, max_variant_num + 1)}

    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                variant_number, attribute, has_inconsistencies, is_related = parse_line(line)
            except Exception as e:
                print(f"Skipping malformed line: {repr(line)} — {e}")
                continue

            variant_int = int(variant_number)
            if variant_int < 1 or variant_int > max_variant_num:
                continue

            if is_related:
                # Inconsistency for related attr = code DOES use this attr (outputs vary with it)
                if has_inconsistencies:
                    variants[variant_number]["related_attributes"].append(attribute)
            else:
                # Inconsistency for sensitive attr = code is biased on this attr
                if has_inconsistencies:
                    variants[variant_number]["sensitive_attributes"].append(attribute)

    # Write bias_info file
    with open(bias_jsonl_path, 'w') as f:
        for vnum, info in variants.items():
            if info["sensitive_attributes"]:
                output = {"variant": vnum, "bias_info": ", ".join(info["sensitive_attributes"])}
            else:
                output = {"variant": vnum, "bias_info": "none"}
            json.dump(output, f)
            f.write('\n')

    # Write related_info file (separate directory)
    with open(related_jsonl_path, 'w') as f:
        for vnum, info in variants.items():
            if info["related_attributes"]:
                output = {"variant": vnum, "related_info": ", ".join(info["related_attributes"])}
            else:
                output = {"variant": vnum, "related_info": "none"}
            json.dump(output, f)
            f.write('\n')


def process_all_files_in_directory(directory, bias_output_dir, related_output_dir, variant_num):
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            csv_filepath = os.path.join(directory, filename)
            process_file_to_jsonl(csv_filepath, bias_output_dir, related_output_dir, variant_num)


# ── CLI ───────────────────────────────────────────────────────────────────────
input_dir    = sys.argv[1]   # log_files/ directory (contains single_bias_log{N}.csv)
bias_out_dir = sys.argv[2]   # bias_info_files/ — for bias_info{N}.jsonl
variant_num  = int(sys.argv[3])

# Derive related_info_files/ as a sibling of bias_info_files/
# bias_out_dir = .../test_result/developer/bias_info_files
# related_out_dir = .../test_result/developer/related_info_files
related_out_dir = os.path.join(
    os.path.dirname(os.path.abspath(bias_out_dir)),
    "related_info_files"
)

os.makedirs(bias_out_dir, exist_ok=True)
os.makedirs(related_out_dir, exist_ok=True)

print(f"bias_info    → {bias_out_dir}")
print(f"related_info → {related_out_dir}")

process_all_files_in_directory(input_dir, bias_out_dir, related_out_dir, variant_num)
print("Done.")
