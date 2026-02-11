# How to Run the Agent Server

## Prerequisites
1.  Ensure you have Python installed.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Server
Run the following command in your terminal:

```bash
uvicorn server:app --reload
```

The server will start at `http://127.0.0.1:8000`.

## API Endpoint
-   **URL**: `http://127.0.0.1:8000/api/chat`
-   **Method**: `POST`
-   **Payload**:
    ```json
    {
      "messages": [], 
      "new_message": "Hello", 
      "conversation_id": "optional-session-id"
    }
    ```
