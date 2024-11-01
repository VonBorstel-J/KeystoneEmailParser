import os

# Define the base directory and structure
base_dir = r"C:\Users\jorda\OneDrive\Desktop\Quickbase Dev Work\KeystoneEmailParser"
frontend_structure = {
    "frontend": {
        "components": {
            "common": ["Header.jsx", "Modal.jsx", "Toast.jsx", "ToastContainer.jsx"],
            "ParsingOverlay": ["ParserForm.jsx", "ProgressBar.jsx", "StatusIndicator.jsx", "index.jsx", "styles.css"],
            "ResultViewer": ["DownloadButton.jsx", "HumanReadable.jsx", "JsonView.jsx", "OriginalView.jsx", "index.jsx", "styles.css"],
            "": ["App.jsx"]
        },
        "actions": ["api.js"],
        "reducers": ["parsingReducer.js", "index.js"],
        "core": ["socketListeners.js", "validation.js"],
        "static": {"css": ["styles.css"]},
        "utils": ["helpers.js"],
        "": ["App.jsx", "index.js"]
    }
}

# Function to create directories and files
def create_structure(base, structure):
    for name, content in structure.items():
        dir_path = os.path.join(base, name)
        if isinstance(content, dict):
            os.makedirs(dir_path, exist_ok=True)
            create_structure(dir_path, content)
        elif isinstance(content, list):
            os.makedirs(dir_path, exist_ok=True)
            for file in content:
                open(os.path.join(dir_path, file), 'a').close()
        else:
            open(os.path.join(base, content), 'a').close()

# Create the structure
create_structure(base_dir, frontend_structure)

# Add additional root-level files
root_files = [
    ".gitattributes", "Stuff.txt", ".pylintrc", ".gitignore", ".env", "README.txt",
    "requirements.txt", "importSchema.json", "postcss.config.js", "merged_codebase.txt",
    ".babelrc", "package.json", "webpack.config.js", "app.py", "package-lock.json",
    "tailwind.config.js", "jsconfig.json"
]
for file in root_files:
    open(os.path.join(base_dir, file), 'a').close()

# Add root-level folders
root_folders = [
    ".vscode", "__pycache__", "parse-mail-pro", "testEmails", ".cache", "logs", 
    "archive", "src", "templates", "staticV1", "codebase_chunks", "node_modules", "tools"
]
for folder in root_folders:
    os.makedirs(os.path.join(base_dir, folder), exist_ok=True)

print("Directory structure created successfully.")
