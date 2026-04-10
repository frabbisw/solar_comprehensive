from textx import metamodel_from_str
import json
import os

# Constants for file paths and global attributes
OUTPUT_FILE = "prompts.jsonl"
TEST_FILE_TEMPLATE = "../fairness_test/test_suites/test_suite_{}.py"
FIXED_ATTRIBUTES = [
    ("gender", "str", "['transgender', 'non-binary', 'male', 'female', 'gender neutral']"),
    ("age", "int", "[28, 30, 31, 44, 45, 46, 59, 60, 61]"),
    ("race", "str", "['asian', 'white', 'black', 'hispanic', 'indian']"),
    ("employment_status", "str", "['employed', 'retired', 'unemployed', 'student']"),
    ("education", "str", "['high school', 'college', 'bachelor', 'master', 'doctor']"),
    ("marital_status", "str", "['single', 'married', 'widowed', 'divorced', 'legally separated']"),
    ("religion", "str", "['christianity', 'islam', 'atheist', 'hinduism', 'buddhism']")
]

# Grammar definition for the metamodel
GRAMMAR = '''
Model:
    'class' name=ID '{'
        attributes=AttributeDefinition+
    '}';

AttributeDefinition:
    'attribute' name=ID ':' type=ID 'in' '[' values=ValueList ']';

ValueList:
    values+=Value (',' values+=Value)*
;

Value:
    FLOAT | INT | QUOTED_STRING
;

FLOAT:
    /[0-9]+\.[0-9]+/
;

INT:
    /[0-9]+/
;

QUOTED_STRING:
    /'[^']*'/
;
'''


class TaskManager:
    """Manages ID counter initialization and prompt writing."""

    def __init__(self, output_file):
        self.output_file = output_file
        self.id_counter = 0
        self._initialize_id_counter()

    def _initialize_id_counter(self):
        """Initialize ID counter based on the existing file."""
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r') as file:
                for line in file:
                    record = json.loads(line)
                    if "task_id" in record:
                        self.id_counter = max(self.id_counter, int(record["task_id"]) + 1)

    def get_next_task_id(self):
        """Retrieve and increment the next task ID."""
        task_id = self.id_counter
        self.id_counter += 1
        return task_id

    def write_prompt(self, class_name, related_attributes, method_name, docstring):
        """Generate a prompt with an auto-incremented task ID and write to the output file."""
        attributes = FIXED_ATTRIBUTES + related_attributes
        attr_strings = [
            f"attribute {name}: {type} in {values}" for name, type, values in attributes
        ]
        dsl_text = f'class {class_name} {{\n' + '\n    '.join(attr_strings) + '\n}'

        # Parse the DSL input and generate the dataclass code
        try:
            model = mm.model_from_str(dsl_text)
            _, prompt_code = generate_dataclass_code(model, method_name, docstring)
        except Exception as e:
            print(f"Parsing error: {e}")
            return

        # Create JSON object and write to file
        task_id = str(self.get_next_task_id())
        json_object = {"task_id": task_id, "prompt": prompt_code.strip() + "\n"}
        with open(self.output_file, 'a') as jsonl_file:
            jsonl_file.write(json.dumps(json_object) + '\n')

        print(f"Class code written to {self.output_file} with task_id {task_id}")


def generate_dataclass_code(model, method_name, docstring):
    """Generate Python code for a dataclass based on the model."""
    class_name = model.name
    attributes = model.attributes

    class_code = f'from dataclasses import dataclass\n\n\n@dataclass\nclass {class_name}:\n'
    class_code += f'    # string in lowercase\n'
    for attr in attributes:
        # Correctly format the values for inline comments
        if attr.type == 'int' or attr.type == 'float':
            values_list = [v for v in attr.values.values]  # Convert numbers to strings
        else:
            values_list = [v.strip("'") for v in attr.values.values]  # Remove extra quotes from strings
        class_code += f'    # {attr.name} {values_list}\n'
        class_code += f'    {attr.name}: {attr.type}\n'

    prompt_code = class_code + f'\n    def {method_name}(self)-> bool\n'
    prompt_code += f'        """{docstring}\n        """\n'

    return class_code, prompt_code


def generate_test_suite(task_id, related_attribute, test_related_attributes, sensitive_attributes, class_name,
                        method_name):
    """Generate a pytest-based test suite for fairness testing."""
    attributes = FIXED_ATTRIBUTES + test_related_attributes
    attr_strings = [
        f"attribute {name}: {type} in {values}" for name, type, values in attributes
    ]
    dsl_text = f'class {class_name} {{\n' + '\n    '.join(attr_strings) + '\n}'

    # Parse the DSL input and generate the dataclass code
    try:
        model = mm.model_from_str(dsl_text)
        class_code, _ = generate_dataclass_code(model, "", "")
    except Exception as e:
        print(f"Parsing error: {e}")
        return

    demographic_data = {}
    for attr in model.attributes:
        if attr.type == 'int' or attr.type == 'float':
            demographic_data[attr.name] = [v for v in attr.values.values]  # Convert numbers to strings
        else:
            demographic_data[attr.name] = [v.strip("'") for v in attr.values.values]  # Remove extra quotes from strings
    formatted_demographic_data = "{\n" + ",\n".join(
        f'    "{k}": {json.dumps(v)}' for k, v in demographic_data.items()
    ) + "\n}"

    # Create Python test suite code
    test_code = f"""
import pytest
from utils import *

# Constants for demographic data and sensitive attributes
DEMOGRAPHIC_DATA = {formatted_demographic_data}
SENSITIVE_ATTRIBUTES = {sensitive_attributes}
RELATED_ATTRIBUTES = {related_attributes}

suite_number = {task_id}
paths = generate_paths(suite_number)
function_namespace = \"{method_name}\"
file_name = paths['file_name']
report_dir = paths['report_dir']
log_dir = paths['log_dir']
FILE_PATH = paths['file_path']

{class_code}

class TestFairness:
    \"\"\"Test suite to assess fairness across different demographic attributes.\"\"\"

    @pytest.fixture(autouse=True, scope="class")
    def setup_class(self):
        setup_test_environment(FILE_PATH, {class_name}, function_namespace)

    @pytest.mark.parametrize("attribute", SENSITIVE_ATTRIBUTES)
    def test_attribute_fairness(self, attribute):
        single_attribute_fairness_test(attribute, DEMOGRAPHIC_DATA, {class_name}, FILE_PATH, report_dir,
                                       log_dir, suite_number, function_namespace)
                                       
    @pytest.mark.parametrize("attribute", RELATED_ATTRIBUTES)
    def test_related_attribute_fairness(self, attribute):
        single_attribute_fairness_test(attribute, DEMOGRAPHIC_DATA, {class_name}, FILE_PATH, report_dir,
                                       log_dir, suite_number, function_namespace, is_related=True)


# Run the test
if __name__ == "__main__":
    pytest.main()
    """

    test_file = TEST_FILE_TEMPLATE.format(task_id)
    with open(test_file, 'w') as py_file:
        py_file.write(test_code)

    print(f"Test suite written to {test_file}")


def read_tasks_from_file(file_path):
    """Read examples from a JSON file."""
    with open(file_path, 'r') as file:
        tasks = json.load(file)
    return tasks


# Create the metamodel from the grammar
mm = metamodel_from_str(GRAMMAR)

TASKS_FILE = "tasks.json"

# Process examples from the file
tasks = read_tasks_from_file(TASKS_FILE)

# Example Usage
task_manager = TaskManager(OUTPUT_FILE)

for task in tasks:
    class_name = task['class_name']
    test_related_attributes = task['test_related_attributes']
    method_name = task['method_name']
    docstring = task['docstring']
    task_manager.write_prompt(class_name, test_related_attributes, method_name, docstring)

    related_attributes = task.get('related_attributes', '')
    sensitive_attributes = task.get('sensitive_attributes', '')
    task_id = task_manager.id_counter - 1
    generate_test_suite(task_id, related_attributes, test_related_attributes,
                        sensitive_attributes, class_name, method_name)
