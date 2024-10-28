# Parabuild

Parabuild is a Python package that provides multi-process building to run multiple versions of a project, like C/C++. More generally, it offers an interface for compiling commands to support any similar language needs.

Specifically, this package was initially designed to test the performance of a complex C++ program with different template parameters. This means the compile speed is slow, and parameters can’t be changed at runtime with a single compile. So, the solution is to copy the entire project files `np` times and use `np` processes to compile and run them in parallel.

## How to use

```bash
pip install -e parabuild
python examples/example.py
```

## Example

Taking a project that outputs template parameters as an example, the following code implements the function of parallel compilation and statistics of the sum of the output.

`parabuild/test/example_project/main.cpp`

```cpp
#include <iostream>

#define N 42

template <int n>
void print() {
    std::cout << n << std::endl;
}

int main() {
    print<N>();
    return 0;
}
```

`parabuild/test/example_project/CMakeLists.txt`

```CMakeLists
cmake_minimum_required(VERSION 3.10)

project(ExampleProject)

set(CMAKE_CXX_STANDARD 11)

add_executable(main main.cpp)
```

`examples/example.py`

```py
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

```

## Detail

`init_commands` indicates how to initialize after copying the project.

```py
def init_work():
    subprocess.run(["cp", "-r", self.project_path, workespace_path],
                    stdout=subprocess.DEVNULL, check=True)
    for command in self.init_commands:
        subprocess.run(command, cwd=workespace_path, stdout=subprocess.DEVNULL, check=True)
```

`post_task_maker` is designed as a closure to handle the running results encountered by a process, such as summation or simply saving them all.

```py
def _default_post_task_maker():
    results = []
    def post_task(x):
        nonlocal results
        results.append(x)
        return results
    return post_task

post_task = self.post_task_maker()
while True:
    kwargs = self.queue.get()
    if kwargs is None:
        break
    output = self.task(**kwargs)
    results = post_task(output)
return results
```

Finally, join will return the results of each process in the form of a list.

For the most important `task` parameters, this function determines how to modify a new version and compile it for execution. The parameters of this function are added to the queue through `add_task_kwargs`, note that our framework will pass the `workspace` parameter to the `task` function to indicate its workspace when a process receives this task.

```py
def task(workspace, n):
    pass

for i in range(10000, 10100):
    pb.add_task_kwargs({"n": i, })
```

## TODO

Separate compilation and execution, with the goal of alternating compilation and execution in a schedulable manner to ensure system environment stability during execution (such as CPU resources)

## Update

### 0.1.1

- Add exclude cp support
- Upgrade to pyproject.toml

### 0.1.0

- First version
