import json

# Function to transform each JSONL row into the desired format
def transform_row(row):
    return {
        "text": (
            "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            "Write the testbench for this verilog code\n\n<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
            f"{row['module_code']}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
            f"{row['testbench']}<|eot_id|>"
        )
    }

# Read JSONL file, process, and write the output
def process_jsonl(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            row = json.loads(line)
            transformed_row = transform_row(row)
            outfile.write(json.dumps(transformed_row) + '\n')

# Example usage
input_file = "HDLBits_data.jsonl"  # Replace with your input JSONL file path
output_file = "output.jsonl"  # Replace with your desired output JSONL file path
process_jsonl(input_file, output_file)

print(f"Transformed data written to {output_file}")
