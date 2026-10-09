import pandas as pd
import json

pd.set_option('display.max_columns', None)  # or use a specific large number if 'None' is too broad
pd.set_option('display.max_rows', None)  # or use a specific large number if 'None' is too broad
pd.set_option('display.width', 1000)  # adjust the width to fit your screen if necessary

def create_table_from_json_file(file_path):
    # Load JSON data from a file
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Convert the JSON data to a list of dictionaries, each representing a row in the table
    rows = []
    for key, value in data.items():
        row = {"ID": key}
        row.update(value.get("attribute_counts", {}))
        row["Objects with Bias"] = value.get("objects_with_bias", 0)
        row["Total Objects"] = value.get("total_objects", 0)
        rows.append(row)

    # Create a DataFrame
    df = pd.DataFrame(rows)

    # Fill NaN values with 0 for better representation, since NaN means the attribute was not present
    df.fillna(0, inplace=True)

    # Convert float to int for columns that are supposed to be integer counts
    df = df.astype({col: 'int' for col in df.columns if col not in ['ID']})

    # Return the DataFrame
    return df


# Usage
file_path = 'GPT_test/aggregated_bias_ratios.json'  # Replace 'data.json' with the path to your JSON file
df = create_table_from_json_file(file_path)
print(df)
