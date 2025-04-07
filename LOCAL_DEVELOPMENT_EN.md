# Using Local Version of cognee in cognee-mcp

## Setup

To use the local version of the cognee package in cognee-mcp, the following changes have been made:

1. In the `cognee-mcp/pyproject.toml` file, the cognee dependency now points to the absolute path to the local package:
   ```
   "cognee[postgres,codegraph,gemini,huggingface] @ file:///absolute/path/to/cognee"
   ```

2. Added a setting to allow direct references to local packages:
   ```
   [tool.hatch.metadata]
   allow-direct-references = true
   ```

## Installation and Updating Dependencies

First, make all scripts executable:

```bash
chmod +x make_scripts_executable.sh
./make_scripts_executable.sh
```

Then install the local cognee package in development mode:

```bash
./install_local_cognee.sh
```

Finally, update the dependencies in cognee-mcp:

```bash
./update_mcp_dependencies.sh
```

## How It Works

The `update_pyproject_with_absolute_path.sh` script automatically generates a pyproject.toml file with the absolute path to the project root directory, which avoids problems with relative paths.

After making these changes, cognee-mcp will use the local version of the cognee package from the project root. This means that any changes made to the cognee code (including prompts) will be immediately available in cognee-mcp without the need to update the package version.

## Important Notes

- When making changes to the dependencies of the cognee package, you also need to update the dependencies in cognee-mcp by running the `update_mcp_dependencies.sh` script.
- If you want to revert to using the version from the repository, change the dependency line in `cognee-mcp/pyproject.toml` to `"cognee[postgres,codegraph,gemini,huggingface]"` and run `uv pip install -e .` in the cognee-mcp directory.