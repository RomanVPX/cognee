# Использование локальной версии cognee в cognee-mcp

## Настройка

Для использования локальной версии пакета cognee в cognee-mcp были внесены следующие изменения:

1. В файле `cognee-mcp/pyproject.toml` зависимость cognee теперь указывает на абсолютный путь к локальному пакету:
   ```
   "cognee[postgres,codegraph,gemini,huggingface] @ file:///absolute/path/to/cognee"
   ```

2. Добавлена настройка для разрешения прямых ссылок на локальные пакеты:
   ```
   [tool.hatch.metadata]
   allow-direct-references = true
   ```

## Установка и обновление зависимостей

Сначала сделайте все скрипты исполняемыми:

```bash
chmod +x make_scripts_executable.sh
./make_scripts_executable.sh
```

Затем установите локальный пакет cognee в режиме разработки:

```bash
./install_local_cognee.sh
```

Затем обновите зависимости в cognee-mcp:

```bash
./update_mcp_dependencies.sh
```

## Как это работает

Скрипт `update_pyproject_with_absolute_path.sh` автоматически генерирует файл pyproject.toml с абсолютным путем к корневой директории проекта, что позволяет избежать проблем с относительными путями.

После внесения изменений, cognee-mcp будет использовать локальную версию пакета cognee из корня проекта. Это означает, что любые изменения, внесенные в код cognee (включая промпты), будут немедленно доступны в cognee-mcp без необходимости обновления версии пакета.

## Важные примечания

- При внесении изменений в зависимости пакета cognee, необходимо также обновить зависимости в cognee-mcp, запустив скрипт `update_mcp_dependencies.sh`.
- Если вы хотите вернуться к использованию версии из репозитория, измените строку зависимости в `cognee-mcp/pyproject.toml` на `"cognee[postgres,codegraph,gemini,huggingface]"` и запустите `uv pip install -e .` в директории cognee-mcp.