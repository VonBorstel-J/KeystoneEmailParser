# move_cache.py
import os
import shutil
from pathlib import Path
import logging

def setup_new_cache_location(new_drive_path: str):
    """
    Sets up a new cache location for HuggingFace models.
    
    Args:
        new_drive_path (str): New path for cache (e.g., "D:/.cache/huggingface")
    """
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("CacheMover")

    try:
        # Convert to Path object
        new_path = Path(new_drive_path)
        old_cache = Path.home() / '.cache' / 'huggingface'
        
        # Create new directory if it doesn't exist
        new_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created new cache directory at: {new_path}")

        # If old cache exists, move its contents
        if old_cache.exists():
            logger.info("Found existing cache, preparing to move files...")
            
            # Get size of old cache
            total_size = sum(f.stat().st_size for f in old_cache.rglob('*') if f.is_file())
            logger.info(f"Total cache size to move: {total_size / (1024**3):.2f} GB")

            # Check if destination has enough space
            free_space = shutil.disk_usage(new_path.drive if new_path.drive else new_path).free
            if free_space < total_size:
                logger.error(f"Not enough space on destination drive! Need {total_size / (1024**3):.2f} GB, "
                           f"but only {free_space / (1024**3):.2f} GB available.")
                return False

            # Move files
            for item in old_cache.iterdir():
                if item.is_file():
                    shutil.move(str(item), str(new_path / item.name))
                    logger.info(f"Moved: {item.name}")
                elif item.is_dir():
                    shutil.move(str(item), str(new_path / item.name))
                    logger.info(f"Moved directory: {item.name}")

            logger.info("Cache movement completed successfully!")

        # Update environment variables
        os.environ['TRANSFORMERS_CACHE'] = str(new_path)
        os.environ['HF_HOME'] = str(new_path)

        # Create a .env file if it doesn't exist or update it
        env_file = Path('.env')
        env_content = []
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_content = f.readlines()

        # Update or add cache locations
        cache_updated = False
        hf_home_updated = False
        
        for i, line in enumerate(env_content):
            if line.startswith('TRANSFORMERS_CACHE='):
                env_content[i] = f'TRANSFORMERS_CACHE={str(new_path)}\n'
                cache_updated = True
            elif line.startswith('HF_HOME='):
                env_content[i] = f'HF_HOME={str(new_path)}\n'
                hf_home_updated = True

        if not cache_updated:
            env_content.append(f'TRANSFORMERS_CACHE={str(new_path)}\n')
        if not hf_home_updated:
            env_content.append(f'HF_HOME={str(new_path)}\n')

        with open(env_file, 'w') as f:
            f.writelines(env_content)

        logger.info(f"Environment configured to use new cache location: {new_path}")
        return True

    except Exception as e:
        logger.error(f"Error during cache setup: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python move_cache.py <new_cache_path>")
        print("Example: python move_cache.py D:/.cache/huggingface")
        sys.exit(1)
    
    new_location = sys.argv[1]
    setup_new_cache_location(new_location)