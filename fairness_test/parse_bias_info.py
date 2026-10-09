"""
fairness_test/parse_bias_info.py

Reads Solar test log CSVs and produces two sets of JSONL files:

  bias_info_files/bias_info{N}.jsonl
      Sensitive attributes whose variation caused inconsistent outputs (bias).

  related_info_files/related_info{N}.jsonl
      Related attributes the code DOES use (V1: outputs differ = attr used).

  With --invert_related (V2 mode):
      related_info_v2_files/related_info{N}.jsonl
      Related attributes the code IGNORES (V2: outputs same = attr missing).

Usage:
  # V1 (default)
  python parse_bias_info.py <log_dir> <bias_output_dir> <variant_num>

  # V2 (inverted related logic)
  python parse_bias_info.py <log_dir> <bias_output_dir> <variant_num> --invert_related
"""

import json
import os
import re
import sys


def parse_line(line):
    parts = line.strip().split(':')
    variant_attribute = parts[0].strip()
    status = ':'.join(parts[1:]).strip()
    variant, attribute_with_prefix = variant_attribute.split(', ', 1)
    variant_number = variant.split(' ')[-1]
    attribute = re.search(r"Attribute '([^']+)'", attribute_with_prefix).group(1)
    has_inconsistencies = 'Inconsistencies found.' in status
    execution_failed = 'Execution failed.' in status
    is_related = "Related" in attribute_with_prefix
    return variant_number, attribute, has_inconsistencies, is_related, execution_failed


def extract_number_from_filename(filepath):
    filename = filepath.split("/")[-1] if "/" in filepath else filepath
    match = re.search(r'(\d+)', filename)
    return match.group(0) if match else None


def process_file_to_jsonl(filepath, bias_output_dir, related_output_dir,
                           max_variant_num, invert_related=False):
    number = extract_number_from_filename(filepath)
    if number is None:
        print(f"Could not extract number from filename {filepath}")
        return

    bias_jsonl_path    = os.path.join(bias_output_dir,    f"bias_info{number}.jsonl")
    related_jsonl_path = os.path.join(related_output_dir, f"related_info{number}.jsonl")

    variants = {str(i): {"sensitive_attributes": [], "related_attributes": [], "failed": False}
                for i in range(1, max_variant_num + 1)}

    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                variant_number, attribute, has_inconsistencies, is_related, execution_failed = parse_line(line)
            except Exception as e:
                print(f"Skipping malformed line: {repr(line)} — {e}")
                continue

            variant_int = int(variant_number)
            if variant_int < 1 or variant_int > max_variant_num:
                continue

            if execution_failed:
                variants[variant_number]["failed"] = True
                continue

            if execution_failed:
                variants[variant_number]["failed"] = True
                continue

            if is_related:
                # V1: inconsistency (outputs differ) = attr IS used → record it
                # V2: NO inconsistency (outputs same) = attr is IGNORED → record it
                should_record = (not has_inconsistencies) if invert_related else has_inconsistencies
                if should_record:
                    variants[variant_number]["related_attributes"].append(attribute)
            else:
                if has_inconsistencies:
                    variants[variant_number]["sensitive_attributes"].append(attribute)

    with open(bias_jsonl_path, 'w') as f:
        for vnum, info in variants.items():
            if info["failed"]:
                output = {"variant": vnum, "bias_info": "failed"}
            elif info["sensitive_attributes"]:
                output = {"variant": vnum, "bias_info": ", ".join(info["sensitive_attributes"])}
            else:
                output = {"variant": vnum, "bias_info": "none"}
            json.dump(output, f)
            f.write('\n')

    with open(related_jsonl_path, 'w') as f:
        for vnum, info in variants.items():
            if info["failed"]:
                output = {"variant": vnum, "related_info": "failed"}
            elif info["related_attributes"]:
                output = {"variant": vnum, "related_info": ", ".join(info["related_attributes"])}
            else:
                output = {"variant": vnum, "related_info": "none"}
            json.dump(output, f)
            f.write('\n')


def process_all_files_in_directory(directory, bias_output_dir, related_output_dir,
                                   variant_num, invert_related=False):
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            process_file_to_jsonl(
                os.path.join(directory, filename),
                bias_output_dir, related_output_dir,
                variant_num, invert_related
            )


# ── CLI ───────────────────────────────────────────────────────────────────────
# Usage:
#   python parse_bias_info.py <log_dir> <bias_out_dir> <variant_num> [--invert_related] [--related_out_dir <dir>]
input_dir      = sys.argv[1]
bias_out_dir   = sys.argv[2]
variant_num    = int(sys.argv[3])
invert_related = "--invert_related" in sys.argv

# Optional: explicit related output dir (used for V2 to avoid wrong file placement)
if "--related_out_dir" in sys.argv:
    idx = sys.argv.index("--related_out_dir")
    related_out_dir = sys.argv[idx + 1]
else:
    related_out_dir = os.path.join(
        os.path.dirname(os.path.abspath(bias_out_dir)),
        "related_info_files"
    )

os.makedirs(bias_out_dir, exist_ok=True)
os.makedirs(related_out_dir, exist_ok=True)

mode = "V2 (invert_related)" if invert_related else "V1 (default)"
print(f"mode:        {mode}")
print(f"bias_info    → {bias_out_dir}")
print(f"related_info → {related_out_dir}")

process_all_files_in_directory(input_dir, bias_out_dir, related_out_dir,
                                variant_num, invert_related)
print("Done.")