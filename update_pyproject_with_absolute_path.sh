#!/bin/bash

# Получаем абсолютный путь к корневой директории проекта
ROOT_DIR=$(cd "$(dirname "$0")" && pwd)

# Создаем временный файл pyproject.toml с абсолютным путем
cat > cognee-mcp/pyproject.toml.new << EOF
[project]
name = "cognee-mcp"
version = "0.2.2"
description = "A MCP server project"
readme = "README.md"
requires-python = ">=3.10"

dependencies = [
    "cognee[postgres,codegraph,gemini,huggingface] @ file://${ROOT_DIR}",
    "mcp==1.5.0",
    "uv>=0.6.3",
]

[[project.authors]]
name = "Rita Aleksziev"
email = "rita@topoteretes.com"

[build-system]
requires = [ "hatchling", ]
build-backend = "hatchling.build"

[tool.hatch.metadata]
allow-direct-references = true

[tool.hatch.build.targets.wheel]
packages = ["src"]

[dependency-groups]
dev = [
    "debugpy>=1.8.12",
]

[project.scripts]
cognee = "src:main"
EOF

# Заменяем оригинальный файл
mv cognee-mcp/pyproject.toml.new cognee-mcp/pyproject.toml

echo "Updated pyproject.toml with absolute path: ${ROOT_DIR}"