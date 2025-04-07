import cognee
import asyncio
import json
import os
import argparse
from contextlib import redirect_stdout
from cognee.modules.search.types import SearchType
from cognee.api.v1.visualize.visualize import visualize_graph

async def process_conversation_from_json(file_path, prune=False):
    # Сброс предыдущих данных только если указан флаг prune
    if prune:
        print("Выполняется сброс предыдущих данных...")
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)

    # Чтение и парсинг JSON-файла
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Преобразование в форматированный текст
    formatted_conversation = ""
    for message in data["messages"]:
        author = "Roman" if message["author"] == "user" else "AI"
        content = message["content"]["text"]
        formatted_conversation += f"{author}: {content}\n\n"

    print(f"\nПодготовлена беседа длиной {len(formatted_conversation)} символов")

    # Добавление и обработка в Cognee
    await cognee.add(formatted_conversation)
    print("Данные добавлены в Cognee, начинаю обработку...")
    await cognee.cognify()
    print("Обработка завершена")

    # Сохранение визуализации
    current_dir = os.getcwd()
    visualization_file = os.path.join(current_dir, "visualizations/graph_visualization.html")
    _ = await visualize_graph(destination_file_path=visualization_file)

    return "Обработка завершена успешно"

if __name__ == '__main__':
    # Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(description='Обработка беседы из JSON-файла')
    parser.add_argument('file_path', help='Путь к JSON-файлу с беседой')
    parser.add_argument('--prune', action='store_true', help='Сбросить предыдущие данные перед обработкой')
    args = parser.parse_args()

    # Запуск обработки с учетом флага prune
    asyncio.run(process_conversation_from_json(args.file_path, args.prune))