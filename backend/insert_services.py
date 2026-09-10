import requests

BASE_URL = "http://127.0.0.1:5000/api/services"

services = [
    {
        "serviceName": "Laundry",
        "description": "Clothes washing and ironing service",
        "unitPrice": 200
    },
    {
        "serviceName": "Room Service",
        "description": "Food delivery to room",
        "unitPrice": 350
    },
    {
        "serviceName": "Spa",
        "description": "Spa and wellness service",
        "unitPrice": 1500
    },
    {
        "serviceName": "Airport Pickup",
        "description": "Airport transportation service",
        "unitPrice": 800
    }
]

for service in services:
    response = requests.post(BASE_URL, json=service)

    print(f"\nAdding Service: {service['serviceName']}")
    print("Status Code:", response.status_code)

    try:
        print("Response:", response.json())
    except:
        print("Could not parse JSON response")