from ..parabuild import Parabuild, ParabuildSubprocessError
import os
import subprocess
import time

def test_parabuild():
    def task(workspace, n):
        def modify_line(file_path=os.path.join(workspace, "main.cpp"), line_no=2, new_content=f"#define N {n}\n"):
            if new_content[-1] != "\n":
                new_content += "\n"
            with open(file_path, "r") as f:
                lines = f.readlines()
            lines[line_no] = new_content
            with open(file_path, "w") as f:
                f.writelines(lines)
                
        def compile():
            subprocess.run(["make"], cwd=os.path.join(workspace, "build"), stdout=subprocess.DEVNULL, check=True)
            
        def run():
            res = subprocess.run(["./main"], cwd=os.path.join(workspace, "build"), capture_output=True, check=True)
            output = res.stdout.decode("utf-8")
            return output
            
        def work():
            modify_line()
            compile()
            return run()

        return work()

    def post_task_maker():
        sum = 0
        def post_task(x):
            nonlocal sum
            sum += int(x)
            return sum
        return post_task

    pb = Parabuild(os.path.join(os.path.dirname(__file__), "example_project"),
                   task,
                   init_commands=[
                    #    ["rm", "-rf", "build"],
                       ["cmake", "-B", "build", "."]
                    ],
                   post_task_maker=post_task_maker,
                   enable_tqdm=True,
                   clean_workspace=True)

    ground_truth = 0

    for i in range(10000, 10000 + 3*os.cpu_count() + 2):
        pb.add_task_kwargs({
            "n": i,
        })
        ground_truth += i

    resutls = pb.join()
    sum = 0
    for result in resutls:
        sum += result
        
    assert sum == ground_truth
    
def test_crash():
    def task(workspace):
        raise Exception("Crash")
    
    pb = Parabuild(os.path.join(os.path.dirname(__file__), "example_project"),
                   task,
                   init_commands=[
                       ["cmake", "-B", "build", "."]
                    ],
                   enable_tqdm=True,
                   clean_workspace=True)

    for i in range(10000, 10000 + 3*os.cpu_count() + 2):
        pb.add_task_kwargs({})

    try:
        pb.join()
    except ParabuildSubprocessError as e:
        pass
    else:
        assert False, "Should raise exception"
    
    
if __name__ == "__main__":
    test_parabuild()
    test_crash()
