import json
import re

original_file = 'HDLBits_data.jsonl'
sampled_80_file = 'sampled_80_percent.jsonl'
remaining_20_file = 'remaining_20_percent.jsonl'

# Regex to catch module top_module(...) ... endmodule inside the text field
module_regex = re.compile(r"(module\s+top_module\s*\(.*?\nendmodule)", re.DOTALL)

# 1) Extract code blocks from the 80% file
used_blocks = set()
with open(sampled_80_file, 'r') as f80:
    for line in f80:
        data = json.loads(line)
        text_field = data.get("text", "")
        # Find all module definitions in "text"
        matches = module_regex.findall(text_field)
        # Store them in a set
        for m in matches:
            used_blocks.add(m.strip())

# 2) Compare original lines' module_code to the extracted blocks
remaining_lines = []
with open(original_file, 'r') as f_orig:
    for line in f_orig:
        data = json.loads(line)
        code = data.get("module_code", "").strip()
        # Check if this code snippet was already “used” (substring check in the set)
        # We do a simple any(...) check to see if the code matches or is contained
        # in any extracted block from the 80% file.
        found_in_80 = any(code in block or block in code for block in used_blocks)
        if not found_in_80:
            remaining_lines.append(line)

# 3) Write out whatever didn’t match
with open(remaining_20_file, 'w') as out:
    out.writelines(remaining_lines)

print(f"Created {remaining_20_file} with remaining lines (approx 20%).")
