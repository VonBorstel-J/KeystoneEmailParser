import os

# Define the list of files you want to include
file_paths = [
    # Original static files
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\App.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\index.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\App.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\common",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\common\\Modal.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\common\\Header.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\common\\Toast.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\common\\ToastContainer.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ParsingOverlay",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ParsingOverlay\\styles.css",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ParsingOverlay\\StatusIndicator.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ParsingOverlay\\ProgressBar.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ParsingOverlay\\index.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ParsingOverlay\\ParserForm.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ResultViewer",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ResultViewer\\styles.css",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ResultViewer\\JsonView.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ResultViewer\\HumanReadable.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ResultViewer\\DownloadButton.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ResultViewer\\OriginalView.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\components\\ResultViewer\\index.jsx",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\reducers",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\reducers\\index.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\reducers\\parsingReducer.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\static\\css",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\static\\css\\styles.css",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\core",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\core\\validation.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\core\\socketListeners.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\actions",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\actions\\api.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\actions\\parsingActions.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\utils",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\utils\\helpers.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\frontend\\utils\\socket.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\src\\parsers\\enhanced_parser.py",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\templates\\index.html",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\webpack.config.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\tailwind.config.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\package.json",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\jsconfig.json",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\app.py",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\.babelrc",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\postcss.config.js",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\importSchema.json",
    "C:\\Users\\jorda\\OneDrive\\Desktop\\Quickbase Dev Work\\KeystoneEmailParser\\.env"
]
# Define the output directory and chunk size
output_dir = "codebase_chunks"
os.makedirs(output_dir, exist_ok=True)
max_chunk_size = 40000  # Adjust this based on the LLM token limits (e.g., 20000 characters)

def merge_files(file_paths):
    """
    Merges the content of all files into a single string with headers.
    """
    merged_content = ""
    for file_path in file_paths:
        if os.path.isfile(file_path):
            # Write a header with the file path
            merged_content += f"\n\n# {'-' * 20} {file_path} {'-' * 20}\n\n"
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    # Optionally filter out import statements or blank lines
                    if line.strip().startswith("import ") or line.strip().startswith("from ") or len(line.strip()) == 0:
                        continue
                    merged_content += line
            merged_content += "\n\n"
        else:
            print(f"Skipped: {file_path} (not a file)")
    return merged_content

def split_into_chunks(content, max_size):
    """
    Splits the merged content into chunks not exceeding max_size characters.
    Attempts to split at the nearest newline before the max_size.
    """
    chunks = []
    while len(content) > 0:
        if len(content) <= max_size:
            chunks.append(content)
            break
        # Find the last newline within max_size
        split_point = content.rfind('\n', 0, max_size)
        if split_point == -1:
            split_point = max_size
        chunk = content[:split_point]
        chunks.append(chunk)
        content = content[split_point:]
    return chunks

def save_chunks(chunks, output_dir):
    """
    Saves each chunk to a separate file in the output directory.
    """
    for i, chunk in enumerate(chunks, start=1):
        chunk_file = os.path.join(output_dir, f"codebase_chunk_{i}.txt")
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(chunk)
        print(f"Saved: {chunk_file}")

def merge_and_split_files(file_paths, output_dir, max_chunk_size):
    """
    Merges all specified files and splits the merged content into chunks.
    """
    print("Merging files...")
    merged_content = merge_files(file_paths)
    print(f"Total merged content size: {len(merged_content)} characters")

    print("Splitting into chunks...")
    chunks = split_into_chunks(merged_content, max_chunk_size)
    print(f"Total chunks created: {len(chunks)}")

    print("Saving chunks...")
    save_chunks(chunks, output_dir)
    print(f"All files have been merged and split into {len(chunks)} chunks in the '{output_dir}' directory.")

# Run the merge and split function
merge_and_split_files(file_paths, output_dir, max_chunk_size)
