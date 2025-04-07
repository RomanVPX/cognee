#!/bin/bash

echo "Installing local cognee package in development mode..."

# Устанавливаем cognee в режиме разработки
poetry install

if [ $? -ne 0 ]; then
    echo "Error: Failed to install cognee package. Please check the error message above."
    exit 1
fi

echo "Local cognee package installed successfully!"
echo "Now you can run ./update_mcp_dependencies.sh to update cognee-mcp dependencies."