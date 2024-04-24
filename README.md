# DynamoDocs

DynamoDocs is an automatic documentation generator tool designed primarily for Python Git repositories. It aims to simplify the process of generating documentation by providing an easy-to-use interface with customizable options.

## Features

-   **Smart Git Integration**: Dynamically connects with Git to ensure that only modified files are updated with new documentation.
-   **Profile Selection**: Choose from different prompt profiles that can be configured in the config file. By default, it uses the 'dev' profile. Users can easily add their own profiles.
-   **Clear Output**: Option to clear the output directory before generating the documentation, ensuring a clean build from scratch.
-   **Connect to Any LLM**: Integrated with Ollama for better portability. Can connect to any Language Model via ollama (eg. codellama, mistral, llama3 etc).
-   **Repository Path Override**: Specify a path to any repository to be documented. Can also be done via the config file.

## Installation

To install DynamoDocs, clone the repository and set up a new virtual environment for it:

```bash
# make sure you have python3 installed with pip
# python --version should return a version >= 3.12.2
git clone https://github.com/niraj-kumar-r/DynamoDocs.git
cd dynamodocs
python -m venv .venv
source .venv/bin/activate # On Windows, use: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Before running DynamoDocs, make sure to configure the `config.ini` file according to your needs. You can set the default profile, repository path, and other options.

Sample `config.ini`:

```ini
[DEFAULT]
repo_path: "./"
# can be overwritten via cli -rp flag
project_hierarchy: .project_hierarchy
max_thread_count: 10
max_document_tokens: 5000
ignore_list: []
whitelist_path: #if whitelist_path is not none, We only generate docs on whitelist
Markdown_Docs_folder: "markdown_docs"
ollama_host: "http://localhost:11434"
ollama_model: "codellama"
debug: False
profile_list: { "dev": "dev_prompt", "test": "high_overview" }
```

The config file needs an ollama host and model to connect to the language model.
Make sure to have the ollama server running before running dynamodocs.
For more information on setting up the ollama server, refer to the [Ollama Repository](https://github.com/ollama/ollama)
By default we use the codellama model running on localhost:11434.

## Usage

Run DynamoDocs using the following command:

```bash
python -m dynamodocs [-h] [-p PROFILE] [-c] [-rp REPO_PATH]
```

### Options

-   **-h, --help**: Show the help message and exit.
-   **-p PROFILE, --profile PROFILE**: Choose the prompt profile to use. Can be configured in the config file. Default is 'dev'.
-   **-c, --clear**: Clear the output directory before generating the documentation from scratch.
-   **-rp REPO_PATH, --repo_path REPO_PATH**: Path to the repository to be documented. If not provided, the repository path in the config file will be used.

## Limitations

-   **Python Only**: Currently, DynamoDocs is optimized for Python Git repositories only. This is because we are using the 'jedi' library for code analysis and reference acquisition, which is Python-specific.

## Contributing

We welcome contributions! If you would like to contribute to DynamoDocs, please create a pull request on the [GitHub repository](https://github.com/niraj-kumar-r/DynamoDocs.git)

## License

DynamoDocs is licensed under the GPLv3 License. See the [LICENSE](LICENSE) file for details.

## Support

For support or any questions, please create an issue on the [GitHub repository](https://github.com/niraj-kumar-r/dynamodocs/issues).

---

Happy documenting with DynamoDocs! 📚🚀
