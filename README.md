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

\`\`\`bash
git clone https://github.com/niraj-kumar-r/DynamoDocs.git
cd dynamodocs
python -m venv .venv
source .venv/bin/activate # On Windows, use: .venv\Scripts\activate
pip install -r requirements.txt
\`\`\`

## Configuration

Before running DynamoDocs, make sure to configure the `config.ini` file according to your needs. You can set the default profile, repository path, and other options.

Sample `config.ini`:

\`\`\`ini
[DEFAULT]
profile = dev
repo_path = /path/to/your/repository
\`\`\`

## Usage

Run DynamoDocs using the following command:

\`\`\`bash
python -m dynamodocs -h
\`\`\`

### Options

-   **-h, --help**: Show the help message and exit.
-   **-p PROFILE, --profile PROFILE**: Choose the prompt profile to use. Can be configured in the config file. Default is 'dev'.
-   **-c, --clear**: Clear the output directory before generating the documentation from scratch.
-   **-rp REPO_PATH, --repo_path REPO_PATH**: Path to the repository to be documented. If not provided, the repository path in the config file will be used.

## Limitations

-   **Python Only**: Currently, DynamoDocs is optimized for Python Git repositories only.

## Contributing

We welcome contributions! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute to DynamoDocs.

## License

DynamoDocs is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For support or any questions, please create an issue on the [GitHub repository](https://github.com/your-username/dynamodocs/issues).

---

Happy documenting with DynamoDocs! 📚🚀
