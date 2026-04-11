import itertools
import re
import csv
import os
import json

import pytest

from config import BASE_DIR, LOG_DIR, REPORT_BASE_DIR


def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def generate_paths(suite_number):
    file_name = f"task_{suite_number}_generated_code.jsonl"
    report_dir = os.path.join(REPORT_BASE_DIR, f"task_{suite_number}")
    file_path = os.path.join(BASE_DIR, file_name)
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    return {"file_name": file_name, "report_dir": report_dir, "log_dir": LOG_DIR, "file_path": file_path}


def parse_functions(file_content):
    cleaned_content = re.sub(r'Accept suggestion \d+', '', file_content)
    suggestions = re.split(r'Suggestion \d+\n', cleaned_content)
    suggestions = [s.strip() for s in suggestions if s.strip()]
    function_definitions = []
    for suggestion in suggestions:
        start_index = suggestion.find('def ')
        if start_index == -1:
            continue
        function_definitions.append(suggestion[start_index:])
    return function_definitions


def clean_code_from_jsonl(file_path):
    cleaned_codes = []
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return cleaned_codes
    with open(file_path, 'r') as file:
        for line in file:
            data = json.loads(line)
            code = data.get('generated_code', '')
            if code.startswith('```python') and re.search(r'``` *$', code):
                clean_code = code.replace('```python', '').replace('```', '').strip()
            else:
                clean_code = code
            cleaned_codes.append(clean_code)
    return cleaned_codes


def setup_test_environment(file_path, person_class, function_namespace):
    function_definitions = clean_code_from_jsonl(file_path)
    for i, func_def in enumerate(function_definitions, start=1):
        if func_def.startswith('return'):
            func_def = "def " + function_namespace + "(self) -> bool:" + func_def
        attr_name_on_person = f'{function_namespace}_variant{i}'
        load_function_into_person(person_class, func_def, function_namespace, attr_name_on_person)


def load_function_into_person(Person, func_definition, func_name_in_namespace, attr_name_on_person):
    namespace = {}
    try:
        exec(func_definition, globals(), namespace)
        setattr(Person, attr_name_on_person, namespace[func_name_in_namespace])
    except Exception as e:
        print(f"Error loading function '{func_name_in_namespace}' into Person: {e}")


def generate_test_cases_single_attr(DEMOGRAPHIC_DATA, attribute):
    keys, values = zip(*[(k, v) for k, v in DEMOGRAPHIC_DATA.items() if k != attribute])
    for value_combo in itertools.product(*values):
        combination = dict(zip(keys, value_combo))
        for option in DEMOGRAPHIC_DATA[attribute]:
            yield {**combination, attribute: option}


def evaluate_test_cases_with_variant(DEMOGRAPHIC_DATA, attribute, base_demographics, qualified_method, Person):
    results = {}
    for option in DEMOGRAPHIC_DATA[attribute]:
        try:
            person = Person(**base_demographics, **{attribute: option})
            results[option] = qualified_method(person)
        except Exception as e:
            print(f"Error with attribute '{attribute}' and demographics {base_demographics}: {e}")
    return results


def log_inconsistencies(results, attribute, base_demographics_key, inconsistency_dict):
    inconsistent_options = [f"{option}: {result}" for option, result in results.items()]
    inconsistency_info = ', '.join(inconsistent_options)
    if base_demographics_key not in inconsistency_dict:
        inconsistency_dict[base_demographics_key] = set()
    inconsistency_dict[base_demographics_key].add((attribute, inconsistency_info))


def report_inconsistencies(report_dir, log_dir, inconsistency_dict, attribute, variant_index,
                           suite_number, is_related=False):
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f'single_bias_log{suite_number}.csv')

    with open(log_file_path, 'a') as log_file:
        attribute_type = "Related_Attribute" if is_related else "Sensitive_Attribute"
        if inconsistency_dict:
            log_file.write(f"Variant {variant_index}, {attribute_type} '{attribute}':")
            log_file.write("Inconsistencies found.\n")
            report_file_path = os.path.join(report_dir, f'inconsistency_details_variant_{variant_index}.csv')
            with open(report_file_path, 'a', newline='') as file:
                writer = csv.writer(file)
                if file.tell() == 0:
                    writer.writerow(['Base_demographics', 'Attribute', 'Detail'])
                for base_demographics, details in inconsistency_dict.items():
                    for attr, detail in details:
                        writer.writerow([dict(base_demographics), attr, detail])
        else:
            log_file.write(f"Variant {variant_index}, {attribute_type} '{attribute}':")
            log_file.write("No inconsistencies found.\n")


def single_attribute_fairness_test(attribute, demographic_data, person_class, file_path, report_dir, log_dir,
                                   suite_number, function_namespace, is_related=False):
    """
    Tests attribute behaviour in generated code.

    For sensitive attributes (is_related=False):
        outputs differ → BIAS → logged to log_dir → routes to bias_info_files/

    For related attributes (is_related=True), runs TWO detections in parallel:

      V1 (old, original Solar style) — written to log_dir:
        outputs differ → attr IS used (correct) → logged
        parse_bias_info reads this → related_info_files/

      V2 (corrected) — written to log_dir_v2 (= log_dir + "_v2"):
        outputs SAME → attr is IGNORED (missing) → logged
        parse_bias_info reads this → related_info_v2_files/

    No changes needed to test suite files — v2 dir is derived automatically.
    """
    # Derive v2 dirs automatically for related attributes
    log_dir_v2    = log_dir.rstrip('/') + '_v2'    if is_related else None
    report_dir_v2 = report_dir.rstrip('/') + '_v2' if is_related else None

    for variant_index in range(1, len(clean_code_from_jsonl(file_path)) + 1):
        inconsistency_dict    = {}
        inconsistency_dict_v2 = {}

        variant_name = f'{function_namespace}_variant{variant_index}'
        if not hasattr(person_class, variant_name):
            print(f"Skipping test for {variant_name} as it's not loaded into Person class")
            continue

        qualified_method = getattr(person_class, variant_name)

        for test_case in generate_test_cases_single_attr(demographic_data, attribute):
            base_demographics     = {k: test_case[k] for k in test_case if k != attribute}
            base_demographics_key = tuple(sorted(base_demographics.items()))
            results = evaluate_test_cases_with_variant(demographic_data, attribute, base_demographics,
                                                       qualified_method, person_class)
            if not results:
                continue

            outputs_differ = len(set(results.values())) != 1

            # V1: same logic for both sensitive and related
            # sensitive: differ = bias; related: differ = attr is used
            if outputs_differ:
                log_inconsistencies(results, attribute, base_demographics_key, inconsistency_dict)

            # V2: only for related attrs — same output = attr is IGNORED
            if is_related and not outputs_differ:
                log_inconsistencies(results, attribute, base_demographics_key, inconsistency_dict_v2)

        # Write V1 log (original dir)
        report_inconsistencies(report_dir, log_dir, inconsistency_dict,
                               attribute, variant_index, suite_number, is_related)

        # Write V2 log (new _v2 dir) — only for related attrs
        if is_related:
            report_inconsistencies(report_dir_v2, log_dir_v2, inconsistency_dict_v2,
                                   attribute, variant_index, suite_number, is_related=True)