import json
import random

# Define the input and output file paths
input_file = 'output.jsonl'
output_file = 'sampled_80_percent.jsonl'

# Read the original file
with open(input_file, 'r') as infile:
    lines = infile.readlines()

# Shuffle and sample 80% of the lines
sample_size = int(0.8 * len(lines))
sampled_lines = random.sample(lines, sample_size)

# Write the sampled lines to a new file
with open(output_file, 'w') as outfile:
    outfile.writelines(sampled_lines)

print(f"Sampled 80% of the data and saved to {output_file}")
