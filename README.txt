Basic Commands

- Display GPU Overview:
  nvidia-smi
  
  Shows a summary of each GPU’s usage, including memory used, memory free, and the list of processes using GPU resources. This command provides a one-time snapshot of the current GPU status.

- Real-Time Monitoring:
  nvidia-smi -l 1
  
  Continuously updates GPU statistics every second (you can adjust the interval by replacing `1` with the desired number of seconds). This is useful for observing GPU memory usage as your application runs.

- Limit Output to Memory Usage Only:
  nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv
  
  Provides a CSV-formatted output of each GPU’s total, used, and free memory. This is ideal for logging or focusing only on memory stats.

- Monitor a Specific GPU:
  nvidia-smi -i <gpu-id> -l 1
  
  Replace <gpu-id> with the ID of your specific GPU (e.g., 0, 1, etc.) to monitor that GPU only. The -l 1 option refreshes every second, similar to the real-time monitoring command above.

#### Additional Commands

- Show GPU Temperature and Utilization:
  nvidia-smi --query-gpu=temperature.gpu,utilization.gpu --format=csv
  
  Outputs the current GPU temperature and utilization percentage, which is helpful for performance tuning and thermal management.

- Log GPU Usage to a File:
  nvidia-smi -l 1 > gpu_usage.log
  
  Logs real-time GPU monitoring output to gpu_usage.log with updates every second. Replace 1 with a custom interval if desired.

- Limit GPU Memory for a Process (Linux-only):
  CUDA_VISIBLE_DEVICES=0 nvidia-smi -i 0 -pl <power-limit>
  
  Limits the power consumption of GPU 0 to <power-limit> watts. This helps in scenarios where reducing power usage or thermal output is needed.

- Terminate a GPU Process:
  nvidia-smi pmon -i <gpu-id>
  
  Lists all processes on a specific GPU, allowing you to identify processes by their PID. Once you know the PID, you can terminate a process using:
  kill -9 <pid>
  
  Replace <pid> with the actual process ID. This is useful for clearing up GPU memory when a process hangs or no longer needs resources.