# Gemini DM - AI Dungeon Master

A textual adventure game powered by Google's Gemini model, acting as an AI Dungeon Master. This project uses a Retrieval Augmented Generation (RAG) system to provide context from game lore, NPCs, and objects.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url> # Replace <repository_url> with the actual URL
    cd <repository_directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the Google API Key:**
    Create a file named `.env` in the root directory of the project and add your Google API key to it:
    ```
    GOOGLE_API_KEY="YOUR_API_KEY_HERE"
    ```
    Replace `"YOUR_API_KEY_HERE"` with your actual Google API key.

## How to Run

Once the setup is complete, you can run the game using the following command:

```bash
python main.py
```

This will start the game interface.
