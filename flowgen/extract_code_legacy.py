import os
import json
import re


def read_json_file(file_path):
    """
    Reads a JSON file and returns its content as a dictionary.

    :param file_path: Path to the JSON file (log.json)
    :return: A dictionary with the content of the JSON file
    """
    with open(file_path, 'r') as file:
        return json.load(file)


def extract_code_from_def(code):
    """
    Extracts the code snippet from the first 'def' to the end of the string.

    :param code: The full Python code string.
    :return: The extracted code starting from 'def' to the end.
    """
    # Find the first occurrence of 'def' and return the code from there to the end
    match = re.search(r'def\s', code)
    if match:
        start_pos = match.start()
        return code[start_pos:]
    return ""  # Return empty if 'def' is not found


def save_generated_code_to_jsonl(generated_code: str, output_file: str):
    """
    Writes the extracted generated code to a JSONL file.

    :param generated_code: The code snippet starting from 'def' to the end to save.
    :param output_file: The path to the JSONL file.
    """
    with open(output_file, 'w') as file:  # Use 'w' to overwrite and ensure only one entry per file
        file.write(json.dumps({"generated_code": generated_code}) + '\n')


def process_log_files_in_directories(base_directory, output_directory):
    """
    Traverse through directories, find log.json files, extract FinalCode, and save the function code (starting from 'def').

    :param base_directory: The base directory to start searching for log.json files
    :param output_ranges: List of ranges for 'i' to create output files for each range
    :param output_directory: The directory where the output JSONL files will be saved
    """
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    log_files = []

    # Collect all log.json file paths
    for root, dirs, files in os.walk(base_directory):
        if 'log.json' in files:
            log_file_path = os.path.join(root, 'log.json')
            log_files.append(log_file_path)

    # Ensure we have enough log files to match the number of output files
    # if len(log_files) < len(output_ranges):
    #     print(f"Not enough log.json files to match the output ranges. Found {len(log_files)} log files.")
    #     return

    # Process each log file and save to respective task_{i}_generated_code.jsonl
    for log_file_path in log_files:
        log_data = read_json_file(log_file_path)
        task_id = log_data.get("task_id", "unknown_task")
        output_file = os.path.join(output_directory, f"task_{task_id}_generated_code.jsonl")
        print(f"Processing {log_file_path} and saving to {output_file}")
        final_code = log_data.get("FinalCode", None)  # Extract the 'FinalCode' field
        if final_code:
            # Extract the code starting from the 'def' keyword
            code_snippet = extract_code_from_def(final_code)
            if code_snippet:
                save_generated_code_to_jsonl(code_snippet, output_file)


# Example usage
base_directory = "workspace"  # Replace with the path where directories with log.json files are located
output_directory = "gpt_raw/response"  # Replace with the desired output directory

process_log_files_in_directories(base_directory,output_directory)

print(f"Generated code snippets have been saved to the folder {output_directory}")
