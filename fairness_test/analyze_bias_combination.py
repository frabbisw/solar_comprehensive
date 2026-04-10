import csv
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import seaborn as sns
import ast


def read_and_aggregate_inconsistencies(file_path, attributes):
    """
    Reads a CSV file and aggregates inconsistencies based on specified attributes,
    including counting occurrences of 'true' and 'false' in the details.

    :param file_path: The path to the CSV file.
    :param attributes: A list of attribute names to consider for aggregation.
    :return: A dictionary with keys as tuples representing attribute combinations,
             and values as another dictionary mapping (attribute, value) to a count of 'true' and 'false'.
    """
    aggregated_data = defaultdict(lambda: defaultdict(lambda: {'true': 0, 'false': 0}))

    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            base_demographics_str = row['Base_demographics']
            attribute = row['Attribute']
            detail = row['Detail']

            # Convert 'Base_demographics' field to a dictionary
            try:
                base_demographics = ast.literal_eval(base_demographics_str.replace("'", '"'))
            except (ValueError, SyntaxError) as e:
                print(f"Error converting 'Base_demographics' to dict: {e}")
                continue

            if attribute in attributes:
                key = tuple(base_demographics.get(attr) for attr in attributes)

                for part in detail.split(', '):
                    value, result = part.split(': ')
                    # Increment the count for 'true' or 'false' under the specific detail value and attribute
                    # combination
                    aggregated_data[key][(attribute, value)][result.lower()] += 1

    return aggregated_data


def analyze_aggregated_data(aggregated_data):
    """
    Analyzes and prints a report of aggregated data, including true and false counts for each detail.

    :param aggregated_data: The aggregated data dictionary.
    """
    print("\nAnalysis of Inconsistencies by Attribute Combinations:")
    for base_key, details in aggregated_data.items():
        print(f"Combination: {base_key}")
        for detail_key, results in details.items():
            attribute, value = detail_key
            true_count, false_count = results['true'], results['false']
            print(
                f"  Tested Attribute: {attribute}, Detail Value: {value}, True Count: {true_count}, False Count: {false_count}")


def summarize_true_combinations(aggregated_data):
    """
    Summarizes all combinations of attributes that have a 'True' value, including multiple 'True' values within the
    same combination, by placing detail values directly into 'Not Specified' placeholders and ensuring no duplicate
    entries.

    :param aggregated_data: The aggregated data dictionary.
    :return: None, prints the summary directly.
    """
    print("\nSummary of Attribute Combinations with True Values:")
    unique_combinations = set()

    for base_key, details in aggregated_data.items():
        true_details = [detail_key[1] for detail_key, results in details.items() if results['true'] > 0]

        if true_details:  # Check if there are any 'True' detail values
            # Handle the 'Not Specified' case by replacing it with each 'True' detail value
            for detail in true_details:
                modified_base_key = list(base_key)  # Convert tuple to list for modification
                for i, item in enumerate(modified_base_key):
                    if item is None:
                        modified_base_key[i] = detail
                        break  # Replace the first 'None' found and then break
                combination_tuple = tuple(modified_base_key)  # Convert back to tuple for set uniqueness
                unique_combinations.add(combination_tuple)

    # Print unique combinations
    for combination in unique_combinations:
        print(f"Combination: {combination}")


# Example usage
file_path = '../Test_Result/GPT_test/inconsistency_files/task_0/inconsistency_details_variant_7.csv'  # Replace with the path to your CSV file
# attributes_to_analyze = ['gender', 'race', 'employment_status',
#                          'education']  # Specify the attributes you're interested in
# attributes_to_analyze = ['gender']
# 'age', 'education', 'race', 'gender'
attributes_to_analyze = ['age', 'education']
# attributes_to_analyze = ['age', 'employment_status', 'education']
aggregated_data = read_and_aggregate_inconsistencies(file_path, attributes_to_analyze)
analyze_aggregated_data(aggregated_data)

# Example usage after your existing code
summarize_true_combinations(aggregated_data)
