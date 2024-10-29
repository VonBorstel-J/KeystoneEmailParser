import torch

# Check if CUDA is available and get the GPU device name
if torch.cuda.is_available():
    print("CUDA is available!")
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")

    # Allocate a small tensor on the GPU to check memory usage
    tensor = torch.rand((1000, 1000), device="cuda")

    # Get the total memory of the GPU
    total_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)  # Convert to GB
    print(f"Total GPU Memory: {total_memory:.2f} GB")

    # Get the currently allocated memory
    allocated_memory = torch.cuda.memory_allocated(0) / (1024 ** 3)  # Convert to GB
    print(f"Allocated Memory: {allocated_memory:.2f} GB")

    # Get the currently cached memory
    cached_memory = torch.cuda.memory_reserved(0) / (1024 ** 3)  # Convert to GB
    print(f"Cached Memory: {cached_memory:.2f} GB")

    # Free the allocated tensor
    del tensor
    torch.cuda.empty_cache()

else:
    print("CUDA is not available.")
