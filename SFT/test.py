

import json

# count avg words of all test in the jsonl file under a certain attribute
def count_avg_words(input_file, attribute):
    with open(input_file, 'r') as infile:
        lines = infile.readlines()
        total_words = 0
        total_tests = 0
        for line in lines:
            row = json.loads(line)
            text = row.get(attribute, "")
            words = text.split()
            total_words += len(words)
            total_tests += 1
        avg_words = total_words / total_tests
        print(avg_words)

# Example usage
input_file = "output_file.jsonl"  # Replace with your input JSONL file path
count_avg_words(input_file, "gold_testbench")


# call count avg words again
