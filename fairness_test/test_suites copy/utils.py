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

    # Ensure the directories exist
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    return {
        "file_name": file_name,
        "report_dir": report_dir,
        "log_dir": LOG_DIR,
        "file_path": file_path
    }


# This method is for copilot to get the cleaned code.
def parse_functions(file_content):
    # Remove "Accept suggestion #" lines from the content
    cleaned_content = re.sub(r'Accept suggestion \d+', '', file_content)

    # Split the content by "Suggestion #" into sections
    suggestions = re.split(r'Suggestion \d+\n', cleaned_content)

    # Remove any leading/trailing whitespace from each suggestion
    suggestions = [suggestion.strip() for suggestion in suggestions if suggestion.strip()]

    function_definitions = []
    for suggestion in suggestions:
        # Find the start of the function definition using "def"
        start_index = suggestion.find('def ')

        # If "def" is not found, skip this suggestion
        if start_index == -1:
            continue

        # Extract the function definition from the start index to the end of the suggestion
        func_def = suggestion[start_index:]

        # Clean up the function definition
        # Ensure there's proper indentation and newlines as needed
        # func_def = re.sub(r'\n\s*', '\n    ', func_def)  # Adjust indentation for consistency
        # func_def = re.sub(r'"""\s*(def)', r'"""\n\1', func_def, flags=re.DOTALL)  # Adjust for docstrings

        # Add the cleaned function definition to the list
        function_definitions.append(func_def)

    return function_definitions


# This method is for gpt_3.5 to get the cleaned code.
def clean_code_from_jsonl(file_path):
    cleaned_codes = []

    # Open and read the JSONL file line by line
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return cleaned_codes
    with open(file_path, 'r') as file:
        for line in file:
            # Parse the JSON object from the line
            data = json.loads(line)

            # Extract the generated code
            code = data.get('generated_code', '')

            # Check and clean the code if it starts with ```python and ends with ```
            if code.startswith('```python') and re.search(r'``` *$', code):
                # Remove the markers
                clean_code = code.replace('```python', '').replace('```', '').strip()
            else:
                # Return the code as is
                clean_code = code

            cleaned_codes.append(clean_code)

    return cleaned_codes


def setup_test_environment(file_path, person_class, function_namespace):
    # content = read_file(FILE_PATH)
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
        # Skipping the test(s) if exec fails
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


def report_inconsistencies(report_dir, log_dir, inconsistency_dict, attribute, variant_index, suite_number, is_related=False):
    # Ensure the report directory exists
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
    """Tests for fairness by checking if the financial aid qualification is consistent across different values of
    a single attribute for each method variant."""
    # Load function variants into the Person class
    # setup_module(file_path, person_class, function_namespace)

    # print(parse_functions(read_file('../../Copilot/output/output0.txt'))[3])
    for variant_index in range(1, len(clean_code_from_jsonl(file_path)) + 1):
        # print(parse_functions(read_file(FILE_PATH)))
        inconsistency_dict = {}
        variant_name = f'{function_namespace}_variant{variant_index}'
        if not hasattr(person_class, variant_name):
            print(f"Skipping test for {variant_name} as it's not loaded into Person class")
            continue
        qualified_method = getattr(person_class, variant_name)
        for test_case in generate_test_cases_single_attr(demographic_data, attribute):
            base_demographics = {k: test_case[k] for k in test_case if k != attribute}
            base_demographics_key = tuple(sorted(base_demographics.items()))  # Convert to a hashable type
            results = evaluate_test_cases_with_variant(demographic_data, attribute, base_demographics,
                                                       qualified_method, person_class)

            if results and len(set(results.values())) != 1:
                log_inconsistencies(results, attribute, base_demographics_key, inconsistency_dict)

        report_inconsistencies(report_dir, log_dir, inconsistency_dict, attribute, variant_index, suite_number,
                               is_related)
