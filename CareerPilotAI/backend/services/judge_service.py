import os
import time
import json
import tempfile
import subprocess
import ast
from backend.utils.logger import app_logger
from backend.database.db import execute_one

class JudgeService:
    TIMEOUT_SECONDS = 2.0

    @staticmethod
    def _create_response(success: bool, status: str, details: str, passed: int = 0, total: int = 0, runtime: int = 0, memory: int = 0, stdout: str = "", stderr: str = "", compiler_output: str = "", failed_case: int = None, expected: str = None, actual: str = None) -> dict:
        failed_case_dict = None
        if status == "Wrong Answer" and failed_case is not None:
            failed_case_dict = {
                "case_number": failed_case,
                "expected": expected,
                "actual": actual
            }

        return {
            "success": success,
            "status": status,
            "passed": passed,
            "total": total,
            "runtime": runtime,
            "memory": memory,
            "compile_error": compiler_output if status == "Compilation Error" else None,
            "runtime_error": stderr if (status in ["Runtime Error", "Time Limit Exceeded", "Memory Limit Exceeded"]) else None,
            "stderr": stderr,
            "stdout": stdout,
            "failed_case": failed_case_dict,
            "ai_metrics": {},
            "execution_details": {
                "expected": expected,
                "actual": actual,
                "compiler_output": compiler_output,
                "details": details
            },
            # Flat attributes for backward compatibility
            "expected": expected,
            "actual": actual,
            "compiler_output": compiler_output,
            "details": details
        }

    @staticmethod
    def evaluate(problem_id: int, code: str, language: str, test_cases: list) -> dict:
        """Main entry point for evaluating code against test cases."""
        app_logger.info(f"[Judge] Evaluating problem {problem_id} in {language} with {len(test_cases)} cases.")
        if not test_cases:
            return JudgeService._create_response(False, "Configuration Error", "No test cases configured for this problem.", 0, 0, 0, 0)
            
        try:
            if language == "python":
                return JudgeService._run_python(code, test_cases)
            elif language == "javascript" or language == "node":
                return JudgeService._run_javascript(code, test_cases)
            elif language in ["c", "cpp"]:
                return JudgeService._run_c_cpp(code, language, test_cases, problem_id)
            elif language == "java":
                return JudgeService._run_java(code, test_cases, problem_id)
            else:
                return JudgeService._create_response(False, "Internal Judge Error", f"Unsupported language: {language}", 0, len(test_cases))
        except Exception as e:
            import traceback
            app_logger.error(f"[Judge] Fatal Error: {str(e)}\n{traceback.format_exc()}")
            return JudgeService._create_response(False, "Internal Judge Error", str(e), 0, len(test_cases))

    @staticmethod
    def _run_python(code: str, test_cases: list) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "solution.py")
            
            # Extract inputs and expected outputs
            tc_data = [{"input": tc["input"], "expected": tc["expected_output"], "is_hidden": tc["is_hidden"]} for tc in test_cases]
            
            wrapper = f"""
import sys, ast, time
import traceback

def main():
    test_cases = {repr(tc_data)}
    # Find the user's function
    user_funcs = [v for k, v in globals().items() if callable(v) and not k.startswith('__') and k not in ('main', 'ast', 'time', 'traceback')]
    if not user_funcs:
        print("ERROR:No function defined in starter code")
        sys.exit(1)
        
    func = user_funcs[0]
    
    for idx, tc in enumerate(test_cases):
        try:
            args = ast.literal_eval(tc['input'])
            if not isinstance(args, tuple):
                args = (args,)
                
            start = time.time()
            res = func(*args)
            duration = int((time.time() - start) * 1000)
            
            print(f"DONE|{{idx}}|{{res}}|{{duration}}")
        except Exception as e:
            print(f"RUNTIME_ERROR|{{idx}}|{{str(e)}}")

if __name__ == '__main__':
    main()
"""
            with open(file_path, "w") as f:
                f.write(code + "\n" + wrapper)
                
            return JudgeService._execute_interpreter_loop(["python3", file_path], test_cases)

    @staticmethod
    def _run_javascript(code: str, test_cases: list) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "solution.js")
            
            tc_data = [{"input": tc["input"], "expected": tc["expected_output"], "is_hidden": tc["is_hidden"]} for tc in test_cases]
            
            wrapper = f"""
const fs = require('fs');

function main() {{
    const testCases = {json.dumps(tc_data)};
    
    let funcName = null;
    const match = {json.dumps(code)}.match(/function\\s+([a-zA-Z_$][0-9a-zA-Z_$]*)\\s*\\(/);
    if (match) {{
        funcName = match[1];
    }}
    
    if (!funcName || typeof eval(funcName) !== 'function') {{
        console.log("ERROR:No function defined");
        process.exit(1);
    }}
    
    const func = eval(funcName);
    
    for (let i = 0; i < testCases.length; i++) {{
        try {{
            let rawInput = testCases[i].input.trim();
            if (rawInput.startsWith('(') && rawInput.endsWith(')')) {{
                rawInput = '[' + rawInput.slice(1, -1) + ']'; // turn tuple into array
            }}
            rawInput = rawInput.replace(/None/g, 'null').replace(/True/g, 'true').replace(/False/g, 'false');
            
            let args = JSON.parse(rawInput);
            if (!Array.isArray(args)) {{ args = [args]; }}
            
            const start = Date.now();
            const res = func.apply(null, args);
            const duration = Date.now() - start;
            
            console.log("DONE|" + i + "|" + JSON.stringify(res) + "|" + duration);
        }} catch(e) {{
            console.log("RUNTIME_ERROR|" + i + "|" + e.message);
        }}
    }}
}}
main();
"""
            with open(file_path, "w") as f:
                f.write(code + "\n" + wrapper)
                
            return JudgeService._execute_interpreter_loop(["node", file_path], test_cases)

    @staticmethod
    def _run_c_cpp(code: str, language: str, test_cases: list, problem_id: int) -> dict:
        app_logger.info(f"[Judge] User function loaded for {language}")
        # Fetch driver from DB
        row = execute_one("SELECT driver_template FROM problem_templates WHERE problem_id = ? AND language = ?", (problem_id, language))
        wrapper = row["driver_template"] if row and row["driver_template"] else ""
        app_logger.info(f"[Judge] Driver generated for {language}")

        with tempfile.TemporaryDirectory() as tmpdir:
            ext = "c" if language == "c" else "cpp"
            src_path = os.path.join(tmpdir, f"merged.{ext}")
            bin_path = os.path.join(tmpdir, "solution")
            
            with open(src_path, "w") as f:
                f.write(code + "\n" + wrapper)
            app_logger.info(f"[Judge] Merged file created at {src_path}")
                
            # Compile
            app_logger.info(f"[Judge] Compilation started for {language}...")
            if language == "c":
                cmd = ["gcc", src_path, "-std=c11", "-O2", "-o", bin_path]
            else:
                cmd = ["g++", src_path, "-std=c++17", "-o", bin_path]

            compile_res = subprocess.run(cmd, capture_output=True, text=True)
            app_logger.info(f"[Judge] Compilation finished for {language}.")
            
            if compile_res.returncode != 0:
                return JudgeService._create_response(False, "Compilation Error", compile_res.stderr.strip(), 0, len(test_cases), 0, 0, "", "", compile_res.stderr.strip())
            
            app_logger.info(f"[Judge] Execution started for {language}...")
            res = JudgeService._execute_binary_loop([bin_path], test_cases)
            app_logger.info(f"[Judge] Execution finished for {language}.")
            app_logger.info(f"[Judge] Judge completed.")
            return res

    @staticmethod
    def _run_java(code: str, test_cases: list, problem_id: int) -> dict:
        app_logger.info(f"[Judge] User function loaded for java")
        # Fetch driver from DB
        row = execute_one("SELECT driver_template FROM problem_templates WHERE problem_id = ? AND language = 'java'", (problem_id,))
        wrapper = row["driver_template"] if row and row["driver_template"] else ""
        app_logger.info(f"[Judge] Driver generated for java")

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "Main.java")
            
            with open(src_path, "w") as f:
                f.write("import java.util.*;\n\n" + code + "\n" + wrapper)
            app_logger.info(f"[Judge] Merged file created at {src_path}")
                
            # Compile
            app_logger.info(f"[Judge] Compilation started for java...")
            compile_res = subprocess.run(["javac", src_path], capture_output=True, text=True)
            app_logger.info(f"[Judge] Compilation finished for java.")
            
            if compile_res.returncode != 0:
                return JudgeService._create_response(False, "Compilation Error", compile_res.stderr.strip(), 0, len(test_cases), 0, 0, "", "", compile_res.stderr.strip())
            
            app_logger.info(f"[Judge] Execution started for java...")
            res = JudgeService._execute_binary_loop(["java", "-cp", tmpdir, "Main"], test_cases)
            app_logger.info(f"[Judge] Execution finished for java.")
            app_logger.info(f"[Judge] Judge completed.")
            return res

    @staticmethod
    def _execute_interpreter_loop(cmd: list, test_cases: list) -> dict:
        """Executes a managed wrapper script that iterates through tests natively."""
        app_logger.info(f"[Judge] Executing managed loop for {cmd[0]}")
        try:
            start_total = time.time()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=JudgeService.TIMEOUT_SECONDS)
            total_runtime = int((time.time() - start_total) * 1000)
            
            if proc.returncode != 0:
                msg = proc.stderr.strip() or proc.stdout.strip()
                return JudgeService._create_response(False, "Runtime Error", msg, 0, len(test_cases), total_runtime, 0, proc.stdout.strip(), proc.stderr.strip())
                
            # Parse output
            lines = proc.stdout.strip().split("\n")
            passed = 0
            
            for idx, tc in enumerate(test_cases):
                # We expect a DONE|idx|res|duration or RUNTIME_ERROR|idx|msg
                expected = tc["expected_output"].replace(" ", "")
                output_line = None
                for line in lines:
                    if line.startswith(f"DONE|{idx}|") or line.startswith(f"RUNTIME_ERROR|{idx}|"):
                        output_line = line
                        break
                        
                if not output_line:
                    msg = f"Failed to execute test case {idx+1}. Process exited early.\n{proc.stdout.strip()}"
                    return JudgeService._create_response(False, "Runtime Error", msg, passed, len(test_cases), total_runtime, 0, proc.stdout.strip(), proc.stderr.strip())
                    
                parts = output_line.split("|", 3)
                if parts[0] == "RUNTIME_ERROR":
                    return JudgeService._create_response(False, "Runtime Error", parts[2], passed, len(test_cases), total_runtime, 0, proc.stdout.strip(), proc.stderr.strip())
                    
                actual = parts[2].replace(" ", "")
                # JS stringify formatting adjustments
                actual = actual.replace('"', "'")
                expected = expected.replace('"', "'")
                
                if actual == expected:
                    passed += 1
                else:
                    details = "Hidden Test Case Failed." if tc["is_hidden"] else f"Expected {tc['expected_output']} but got {parts[2]}"
                    return JudgeService._create_response(False, "Wrong Answer", details, passed, len(test_cases), total_runtime, 0, proc.stdout.strip(), proc.stderr.strip(), "", idx + 1, tc['expected_output'], parts[2])
                    
            return JudgeService._create_response(True, "Accepted", f"All {passed} test cases passed.", passed, len(test_cases), total_runtime, 1024, proc.stdout.strip(), proc.stderr.strip())
            
        except subprocess.TimeoutExpired:
            return JudgeService._create_response(False, "Time Limit Exceeded", f"Execution timed out after {JudgeService.TIMEOUT_SECONDS}s", 0, len(test_cases), int(JudgeService.TIMEOUT_SECONDS * 1000), 0)

    @staticmethod
    def _execute_binary_loop(cmd: list, test_cases: list) -> dict:
        """Executes a binary by passing inputs to stdin sequentially."""
        passed = 0
        total_time = 0
        stdout_acc = []
        stderr_acc = []
        
        for idx, tc in enumerate(test_cases):
            raw_input = tc["input"]
            expected = tc["expected_output"].strip().replace(" ", "")
            
            try:
                start = time.time()
                proc = subprocess.run(cmd, input=raw_input, capture_output=True, text=True, timeout=JudgeService.TIMEOUT_SECONDS)
                duration = int((time.time() - start) * 1000)
                total_time += duration
                stdout_acc.append(proc.stdout.strip())
                stderr_acc.append(proc.stderr.strip())
                
                if proc.returncode != 0:
                    msg = proc.stderr.strip() or "Segmentation fault or non-zero exit"
                    return JudgeService._create_response(False, "Runtime Error", msg, passed, len(test_cases), total_time, 0, "\n".join(stdout_acc), "\n".join(stderr_acc))
                    
                actual = proc.stdout.strip().replace(" ", "")
                if actual == expected:
                    passed += 1
                else:
                    details = "Hidden Test Case Failed." if tc["is_hidden"] else f"Expected {tc['expected_output']} but got {proc.stdout.strip()}"
                    return JudgeService._create_response(False, "Wrong Answer", details, passed, len(test_cases), total_time, 0, "\n".join(stdout_acc), "\n".join(stderr_acc), "", idx + 1, tc['expected_output'], proc.stdout.strip())
                    
            except subprocess.TimeoutExpired:
                return JudgeService._create_response(False, "Time Limit Exceeded", f"Execution timed out after {JudgeService.TIMEOUT_SECONDS}s", passed, len(test_cases), int(JudgeService.TIMEOUT_SECONDS * 1000), 0, "\n".join(stdout_acc), "\n".join(stderr_acc))
                
        return JudgeService._create_response(True, "Accepted", f"All {passed} test cases passed.", passed, len(test_cases), total_time, 1024, "\n".join(stdout_acc), "\n".join(stderr_acc))
