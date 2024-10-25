from parabuild import Parabuild
import os
import subprocess

def main():
    def task(workspace, n):
        file_path=os.path.join(workspace, "main.cpp")
        with open(file_path, "r") as f:
            lines = f.readlines()
        lines[2] = f"#define N {n}\n"
        with open(file_path, "w") as f:
            f.writelines(lines)
            
        subprocess.run(["make"], cwd=os.path.join(workspace, "build"), stdout=subprocess.DEVNULL, check=True)
        res = subprocess.run(["./main"], cwd=os.path.join(workspace, "build"), capture_output=True, check=True)
        output = res.stdout.decode("utf-8")
        return output

    def post_task_maker():
        sum = 0
        def post_task(x):
            nonlocal sum
            sum += int(x)
            return sum
        return post_task

    pb = Parabuild("parabuild/test/example_project",
                   task,
                   init_commands=[["cmake", "-B", "build", "."]],
                   post_task_maker=post_task_maker,
                   enable_tqdm=True,
                   clean_workspace=True)

    ground_truth = 0

    for i in range(10000, 10100):
        pb.add_task_kwargs({"n": i, })
        ground_truth += i

    resutls = pb.join()
    
    sum = 0
    for result in resutls:
        sum += result
        
    assert sum == ground_truth
    
if __name__ == "__main__":
    main()
