import requests
import json
import sys

# URL del endpoint
url = "http://localhost:8000/api/chat"

# Payload de prueba
payload = {
    "messages": [],
    "new_message": "Hola, ¿cómo estás? ¿Puedes ayudarme a agendar una reunión?",
    "conversation_id": "test-session-1"
}

headers = {
    "Content-Type": "application/json"
}

print(f"Probando endpoint: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    print("\nRespuesta Exitosa:")
    print("Status Code:", response.status_code)
    try:
        print("Response Body:", json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        print("Response Text:", response.text)
except requests.exceptions.HTTPError as err:
    print(f"\nError HTTP: {err}")
    if response:
        print(f"Detalle: {response.text}") 
except Exception as e:
    print(f"\nError de Conexión o Otro: {e}")
