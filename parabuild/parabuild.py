from multiprocessing import Process, Queue
import subprocess
import os
import time

class ParabuildSubprocessError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
        

class Parabuild:
    def _default_post_task_maker():
        results = []
        def post_task(x):
            nonlocal results
            results.append(x)
            return results
        return post_task
    
    def __init__(self,
                 project_path,
                 task,
                 init_commands = [
                    ["rm", "-rf", "build"],
                    ["cmake", "-B", "build", "."]
                ],
                 post_task_maker=_default_post_task_maker,
                 excludes=[],
                 workspace_dir=None,
                 num_workers=None,
                 enable_tqdm=True,
                 clean_workspace=False
                 ):
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project path {project_path} does not exist")
        self.project_path = project_path
        self.task = task
        self.init_commands = init_commands
        self.num_workers = num_workers if num_workers else os.cpu_count()
        self.workspace_dir = workspace_dir if workspace_dir else "parabuild_workspace"
        self.enable_tqdm = enable_tqdm
        self.post_task_maker = post_task_maker
        self.excludes = excludes
        if clean_workspace and os.path.exists(self.workspace_dir):
            subprocess.run(["rm", "-rf", self.workspace_dir], stdout=subprocess.DEVNULL, check=True)
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir, exist_ok=True)

        self.queue = Queue()
        self.result_queue = Queue()
        self.error_queue = Queue()
        self.workers = []
        
        init_workers =[]
        for i in range(self.num_workers):
            workespace_path = f"{self.workspace_dir}/worker_{i}"
            def init_work():
                # subprocess.run(["cp", "-r", self.project_path, workespace_path],
                #                stdout=subprocess.DEVNULL, check=True)
                exclude_str = " ".join([f"--exclude={exclude}" for exclude in self.excludes])
                # mkdir -p "parabuild_workspace/worker_0" && tar -cpP --exclude=.git --exclude=build -C "parabuild/test/example_project" . | tar -xpP -C "parabuild_workspace/worker_0"
                subprocess.run(f'mkdir -p "{workespace_path}"', shell=True, stdout=subprocess.DEVNULL, check=True)
                os.system(f'tar -cpP {exclude_str} -C "{self.project_path}" . | tar -xpP -C "{workespace_path}"')
                for command in self.init_commands:
                    subprocess.run(command, cwd=workespace_path, stdout=subprocess.DEVNULL, check=True)
            init_worker = Process(target=init_work)
            init_workers.append(init_worker)
            init_worker.start()

        for init_worker in init_workers:
            init_worker.join()
        
        if enable_tqdm:
            self.pbar_process = Queue()
        
        self.start()

    def start(self):
        def work(workspace):
            post_task = self.post_task_maker()
            results = None
            while True:
                try:
                    kwargs = self.queue.get()
                    if kwargs is None:
                        break
                    kwargs.update({"workspace": workspace})
                    output = self.task(**kwargs)
                    results = post_task(output)
                except Exception as e:
                    self.error_queue.put(e)
                    e2 = Exception(f"Error in subprocess {workspace}: {e}, kwargs: {kwargs}")
                    raise e2 from e
                if self.enable_tqdm:
                    self.pbar_process.put(1)
            self.result_queue.put(results)

        for i in range(self.num_workers):
            workespace_path = f"{self.workspace_dir}/worker_{i}"
            worker = Process(target=work, args=(workespace_path,))
            self.workers.append(worker)

        for worker in self.workers:
            worker.start()

    def add_task_kwargs(self, task):
        self.queue.put(task)

    def join(self, total_tasks = None):
        if total_tasks is None:
            total_tasks = self.queue.qsize()
        
        if self.enable_tqdm:
            import tqdm
            pbar = tqdm.tqdm(total=total_tasks)

        for _ in range(self.num_workers):
            self.queue.put(None)

        if self.enable_tqdm:
            for _ in range(total_tasks):
                while self.pbar_process.empty():
                    if not self.error_queue.empty():
                        raise ParabuildSubprocessError(f"tqdm stopped due to an error in subprocess {self.error_queue.get()}")
                    time.sleep(0.2)
                    
                self.pbar_process.get()
                pbar.update(1)

            pbar.close()

        for worker in self.workers:
            worker.join()
        
        results = []
        for _ in range(self.num_workers):
            result = self.result_queue.get()
            results.append(result)
        return results
