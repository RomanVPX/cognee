#!/bin/bash

echo "Updating cognee-mcp dependencies to use local cognee package..."

# Сначала обновляем pyproject.toml с абсолютным путем
./update_pyproject_with_absolute_path.sh

cd cognee-mcp || exit

# Удаляем старый lock-файл, если он существует
rm -f uv.lock

# Проверяем, установлен ли пакет cognee в корневой директории
if [ ! -d "../cognee" ]; then
    echo "Error: cognee package not found in the parent directory."
    exit 1
fi

# Устанавливаем зависимости с использованием локального пакета cognee
echo "Installing dependencies with local cognee package..."
uv pip install -e .

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies. Please check the error message above."
    echo "You might need to install the cognee package in development mode first:"
    echo "cd .. && poetry install"
    exit 1
fi

echo "Dependencies updated successfully!"