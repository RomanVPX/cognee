import cognee
import asyncio
import json
import os
import argparse
from cognee.shared.logging_utils import get_logger
from cognee.modules.metrics.operations import get_pipeline_run_metrics
from cognee.api.v1.visualize.visualize import visualize_graph

async def process_conversation_from_json(file_path, prune=False):
    #  Reset data and system state if --prune flag is set
    if prune:
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
    # Print first 10 lines of the conversation
    first_10_lines = "\n".join(formatted_conversation.split("\n")[:10])
    print("\nПервые 10 строк беседы:")
    print(first_10_lines)

    # Добавление и обработка в Cognee
    await cognee.add(formatted_conversation)
    print("Данные добавлены в Cognee, начинаю обработку...")

    # Define ontology path - use the common ontology directory in the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ontology_dir = os.path.join(project_root, "ontology")
    os.makedirs(ontology_dir, exist_ok=True)
    ontology_path = os.path.join(ontology_dir, "dialog_ontology.owl")

    if os.path.exists(ontology_path):
        print(f"Using existing ontology: {ontology_path}")
        pipeline_run = await cognee.cognify(ontology_file_path=ontology_path)
    else:
        print(f"Ontology not found in {ontology_path}, continuing without it")
        pipeline_run = await cognee.cognify()

    # Calculate descriptive metrics
    await get_pipeline_run_metrics(pipeline_run, include_optional=True)
    print("Descriptive graph metrics saved to database.")

    print("Processing complete")

    # Сохранение визуализации
    current_dir = os.getcwd()
    visualization_file = os.path.join(current_dir, "visualizations/graph_visualization.html")
    _ = await visualize_graph(destination_file_path=visualization_file)

    return "Processing complete successfully"

if __name__ == '__main__':
    logger = get_logger()
    # Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(description='Обработка беседы из JSON-файла')
    parser.add_argument('file_path', help='Путь к JSON-файлу с беседой')
    parser.add_argument('--prune', action='store_true', help='Сбросить предыдущие данные перед обработкой')
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(process_conversation_from_json(args.file_path, args.prune))
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())