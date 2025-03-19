import asyncio
import concurrent.futures
import json
from azure_ai_openai import AsyncAzureOpenAI

# Configure the Azure OpenAI client
AZURE_OPENAI_API_KEY = "your_api_key_here"
timeout = 30
client = AsyncAzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-10-21",
    azure_endpoint="",
    timeout=timeout
)


def extract_xml_answer(text: str) -> str:
    answer = text.split("<answer>")[-1]
    answer = answer.split("</answer>")[0]
    return answer.strip()

async def evaluate_completion(eval_prompt: str, model: str = "your_deployment_model") -> dict:
    """
    Asynchronously calls Azure OpenAI with a structured response format.
    Returns the parsed JSON containing 'reasoning' and 'score'.
    """
    response = await client.chat.completions.acreate(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert Verilog evaluator. Evaluate the following candidate testbench against the expected reference. Provide some reasoning (keep it relatively short) and then your final numerical score in a JSON format as follows:"},
            {"role": "user", "content": eval_prompt}
        ],
        temperature=0.0,
        max_tokens=100,
        response_format={
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "The model's reasoning process leading to the score."
                },
                "score": {
                    "type": "number",
                    "description": "The model's evaluation score for the testbench.",
                    "enum": [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
                }
            },
            "required": ["reasoning", "score"],
            "additionalProperties": False
        }
    )
    # Assume the structured output is returned in the function_call field
    return json.loads(response.choices[0].message["function_call"]["arguments"])

def azure_llm_correctness_reward_func(prompts, completions, answer, client, model: str = "your_deployment_model") -> list[float]:
    """
    For each candidate testbench (completion), builds an evaluation prompt that instructs the LLM to output a structured JSON.
    The JSON includes both its chain-of-thought reasoning and a final numeric score (0.0 to 2.0).
    Returns a list of scores.
    """
    # Extract the question from the last message in the first prompt group.
    question = prompts[0][-1]['content']
    
    async def get_evaluation(candidate: str) -> dict:
        eval_prompt = f"""
        Question:
        {question}

        Candidate Testbench:
        {candidate}

        Expected Testbench (Reference):
        {answer[0]}
        """

        return await evaluate_completion(eval_prompt, model)
    
    # Use a ThreadPoolExecutor to run asynchronous evaluations concurrently
    def run_evaluation(candidate: str) -> dict:
        return asyncio.run(get_evaluation(candidate))
    
    scores = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_evaluation, comp[0]['content']) for comp in completions]
        for future in concurrent.futures.as_completed(futures):
            eval_result = future.result()
            scores.append(eval_result.get("score", 0))
    
    # Debug: print a sample evaluation
    if scores:
        print("-" * 20)
        print("Sample evaluation result (structured output):")
        print(eval_result)
    
    return scores

# --- Testing Section ---
if __name__ == "__main__":
    # Dummy prompt: a sample evaluation description.

    data = [
            {"task_id": "mux2to1v", "task_number": 1, "description": "Create a 2-1 multiplexer. When sel=0, choose a. When sel=1, choose b.", "header": "module top_module (\n\tinput [99:0] a,\n\tinput [99:0] b,\n\tinput sel,\n\toutput [99:0] out\n);\n", "module_code": "module top_module (\n\tinput [99:0] a,\n\tinput [99:0] b,\n\tinput sel,\n\toutput [99:0] out\n);\n\n\tassign out = sel ? b : a;\n\t\nendmodule\n", "testbench": "`timescale 1 ps/1 ps\n`define OK 12\n`define INCORRECT 13\nmodule reference_module (\n\tinput [99:0] a,\n\tinput [99:0] b,\n\tinput sel,\n\toutput [99:0] out\n);\n\n\tassign out = sel ? b : a;\n\t\nendmodule\n\n\nmodule stimulus_gen (\n\tinput clk,\n\toutput logic [99:0] a,b,\n\toutput logic sel,\n\toutput reg[511:0] wavedrom_title,\n\toutput reg wavedrom_enable\t\n);\n\n\n// Add two ports to module stimulus_gen:\n//    output [511:0] wavedrom_title\n//    output reg wavedrom_enable\n\n\ttask wavedrom_start(input[511:0] title = \"\");\n\tendtask\n\t\n\ttask wavedrom_stop;\n\t\t#1;\n\tendtask\t\n\n\n\t\n\tinitial begin\n\t\ta <= 'hdeadbeef;\n\t\tb <= 'h5eaf00d;\n\t\tsel <= 0;\n\t\t@(negedge clk);\n\t\twavedrom_start(\"Beef or seafood?\");\n\t\t\trepeat(6) @(posedge clk) sel <= ~sel;\n\t\t@(negedge clk);\n\t\twavedrom_stop();\n\t\trepeat(100) @(posedge clk, negedge clk)\n\t\t\t{a,b,sel} <= {$random, $random, $random, $random, $random, $random, $random};\n\t\t$finish;\n\tend\n\t\nendmodule\n\nmodule tb();\n\n\ttypedef struct packed {\n\t\tint errors;\n\t\tint errortime;\n\t\tint errors_out;\n\t\tint errortime_out;\n\n\t\tint clocks;\n\t} stats;\n\t\n\tstats stats1;\n\t\n\t\n\twire[511:0] wavedrom_title;\n\twire wavedrom_enable;\n\tint wavedrom_hide_after_time;\n\t\n\treg clk=0;\n\tinitial forever\n\t\t#5 clk = ~clk;\n\n\tlogic [99:0] a;\n\tlogic [99:0] b;\n\tlogic sel;\n\tlogic [99:0] out_ref;\n\tlogic [99:0] out_dut;\n\n\tinitial begin \n\t\t$dumpfile(\"wave.vcd\");\n\t\t$dumpvars(1, stim1.clk, tb_mismatch ,a,b,sel,out_ref,out_dut );\n\tend\n\n\n\twire tb_match;\t\t// Verification\n\twire tb_mismatch = ~tb_match;\n\t\n\tstimulus_gen stim1 (\n\t\t.clk,\n\t\t.* ,\n\t\t.a,\n\t\t.b,\n\t\t.sel );\n\treference_module good1 (\n\t\t.a,\n\t\t.b,\n\t\t.sel,\n\t\t.out(out_ref) );\n\t\t\n\ttop_module top_module1 (\n\t\t.a,\n\t\t.b,\n\t\t.sel,\n\t\t.out(out_dut) );\n\n\t\n\tbit strobe = 0;\n\ttask wait_for_end_of_timestep;\n\t\trepeat(5) begin\n\t\t\tstrobe <= !strobe;  // Try to delay until the very end of the time step.\n\t\t\t@(strobe);\n\t\tend\n\tendtask\t\n\n\t\n\tfinal begin\n\t\tif (stats1.errors_out) $display(\"Hint: Output '%s' has %0d mismatches. First mismatch occurred at time %0d.\", \"out\", stats1.errors_out, stats1.errortime_out);\n\t\telse $display(\"Hint: Output '%s' has no mismatches.\", \"out\");\n\n\t\t$display(\"Hint: Total mismatched samples is %1d out of %1d samples\\n\", stats1.errors, stats1.clocks);\n\t\t$display(\"Simulation finished at %0d ps\", $time);\n\t\t$display(\"Mismatches: %1d in %1d samples\", stats1.errors, stats1.clocks);\n\tend\n\t\n\t// Verification: XORs on the right makes any X in good_vector match anything, but X in dut_vector will only match X.\n\tassign tb_match = ( { out_ref } === ( { out_ref } ^ { out_dut } ^ { out_ref } ) );\n\t// Use explicit sensitivity list here. @(*) causes NetProc::nex_input() to be called when trying to compute\n\t// the sensitivity list of the @(strobe) process, which isn't implemented.\n\talways @(posedge clk, negedge clk) begin\n\n\t\tstats1.clocks++;\n\t\tif (!tb_match) begin\n\t\t\tif (stats1.errors == 0) stats1.errortime = $time;\n\t\t\tstats1.errors++;\n\t\tend\n\t\tif (out_ref !== ( out_ref ^ out_dut ^ out_ref ))\n\t\tbegin if (stats1.errors_out == 0) stats1.errortime_out = $time;\n\t\t\tstats1.errors_out = stats1.errors_out+1'b1; end\n\n\tend\nendmodule\n"}
    ]
    prompts = [
        [
            {"role": "user", "content": f"{item['description']}\n\n{item['module_code']}"}
        ]
        for item in data
    ]
    
    testbenches = []

    # Create completions from "testbench" in data for every item in data
    completions = [
        [{"role": "assistant", "content": item["testbench"]}]
        for item in data
    ]
    
    reference_testbench = "Reference Answer"
    answer = [reference_testbench]
    
    rewards = azure_llm_correctness_reward_func(prompts, completions, answer, client)
    print("Rewards:", rewards)
