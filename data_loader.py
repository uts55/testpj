import os
import json
import logging
from config import CHUNK_SIZE, CHUNK_OVERLAP

# --- Logging Configuration ---
logger = logging.getLogger(__name__)

# --- Function Definitions ---
def split_text_into_chunks(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    if chunk_overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")
    chunks = []
    start_index = 0
    while start_index < len(text):
        end_index = start_index + chunk_size
        actual_end_index = min(end_index, len(text))
        chunks.append(text[start_index:actual_end_index])
        start_index += chunk_size - chunk_overlap
    return chunks

def load_documents(source_paths: list[str]) -> list[dict]:
    documents = []
    for path in source_paths:
        if os.path.isfile(path):
            if path.endswith(".json"):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            documents.extend(data)
                        elif isinstance(data, dict):
                            documents.append(data)
                        else:
                            logger.warning(f"Unexpected JSON structure in {path}. Expected list or dict at root.")
                except FileNotFoundError:
                    logger.error(f"File not found - {path}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON format in - {path}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while processing {path}: {e}")
            else:
                logger.warning(f"Skipping non-JSON file: {path}")
        elif os.path.isdir(path):
            for filename in os.listdir(path):
                filepath = os.path.join(path, filename)
                if os.path.isfile(filepath) and filename.endswith(".json"):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                documents.extend(data)
                            elif isinstance(data, dict):
                                documents.append(data)
                            else:
                                logger.warning(f"Unexpected JSON structure in {filepath}. Expected list or dict at root.")
                    except FileNotFoundError: 
                        logger.error(f"File not found - {filepath}")
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON format in - {filepath}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while processing {filepath}: {e}")
                elif os.path.isfile(filepath): 
                    logger.warning(f"Skipping non-JSON file: {filepath}")
        else:
            logger.warning(f"Source path not found or invalid, skipping: {path}")
    return documents

def _get_nested_value(doc: dict, key_path: str):
    keys = key_path.split('.')
    value = doc
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list): 
            try:
                idx = int(key)
                if 0 <= idx < len(value):
                    value = value[idx]
                else:
                    return None 
            except ValueError: # Not an integer index
                return None 
        else: # Key not found or value is not a collection
            return None 
    return value

def filter_documents(documents: list[dict], filters: dict) -> list[dict]:
    filtered_docs = []
    for doc in documents:
        match = True
        for key_path, expected_value in filters.items():
            actual_value = _get_nested_value(doc, key_path)
            if actual_value != expected_value:
                match = False
                break
        if match:
            filtered_docs.append(doc)
    return filtered_docs

def _extract_text_from_value(value) -> list[str]:
    texts = []
    if isinstance(value, str):
        texts.append(value)
    elif isinstance(value, list):
        for item in value:
            texts.extend(_extract_text_from_value(item))
    elif isinstance(value, dict):
        for sub_value in value.values():
            texts.extend(_extract_text_from_value(sub_value))
    return texts

def extract_text_for_rag(document: dict, text_fields: list[str]) -> str:
    extracted_texts = []
    for field_path in text_fields:
        value = _get_nested_value(document, field_path)
        if value is not None:
            texts_from_field = _extract_text_from_value(value)
            extracted_texts.extend(texts_from_field)
    return " ".join(extracted_texts)
