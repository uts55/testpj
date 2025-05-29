import os
import json
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter # Added
from config import CHUNK_SIZE, CHUNK_OVERLAP

# --- Logging Configuration ---
logger = logging.getLogger(__name__)

# --- Function Definitions ---
def split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]: # Modified
    """Splits text into chunks using RecursiveCharacterTextSplitter.""" # Added
    if chunk_overlap >= chunk_size: # Added
        raise ValueError("Chunk overlap must be smaller than chunk size.") # Added
    text_splitter = RecursiveCharacterTextSplitter( # Added
        chunk_size=chunk_size, # Added
        chunk_overlap=chunk_overlap, # Added
        length_function=len, # Added
        is_separator_regex=False, # Added
    ) # Added
    return text_splitter.split_text(text) # Added

def load_documents(source_paths: list[str]) -> list[dict]:
    documents = []
    for path in source_paths:
        if os.path.isfile(path):
            if path.endswith(".json"):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        metadata = {"source": path, "document_type": "json"}
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    item["_metadata"] = metadata
                            documents.extend(data)
                        elif isinstance(data, dict):
                            data["_metadata"] = metadata
                            documents.append(data)
                        else:
                            logger.warning(f"Unexpected JSON structure in {path}. Expected list or dict at root.")
                except FileNotFoundError:
                    logger.error(f"File not found - {path}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON format in - {path}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while processing {path}: {e}")
            elif path.endswith(".txt"): # Added .txt file handling
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        metadata = {"source": path, "document_type": "txt"}
                        documents.append({"text_content": content, "_metadata": metadata})
                except FileNotFoundError:
                    logger.error(f"File not found - {path}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while processing {path}: {e}")
            else:
                logger.warning(f"Skipping non-JSON or non-TXT file: {path}") # Modified log message
        elif os.path.isdir(path):
            for filename in os.listdir(path):
                filepath = os.path.join(path, filename)
                if os.path.isfile(filepath) and filename.endswith(".json"):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            metadata = {"source": filepath, "document_type": "json"} # Added metadata
                            if isinstance(data, list):
                                for item in data: # Added loop for metadata
                                    if isinstance(item, dict): # Added check for metadata
                                        item["_metadata"] = metadata # Added metadata
                                documents.extend(data)
                            elif isinstance(data, dict):
                                data["_metadata"] = metadata # Added metadata
                                documents.append(data)
                            else:
                                logger.warning(f"Unexpected JSON structure in {filepath}. Expected list or dict at root.")
                    except FileNotFoundError: 
                        logger.error(f"File not found - {filepath}")
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON format in - {filepath}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while processing {filepath}: {e}")
                elif os.path.isfile(filepath) and filename.endswith(".txt"): # Added .txt file handling for directories
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            metadata = {"source": filepath, "document_type": "txt"}
                            documents.append({"text_content": content, "_metadata": metadata})
                    except FileNotFoundError:
                        logger.error(f"File not found - {filepath}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while processing {filepath}: {e}")
                elif os.path.isfile(filepath): 
                    logger.warning(f"Skipping non-JSON or non-TXT file: {filepath}") # Modified log message
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
