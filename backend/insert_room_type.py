import requests

BASE_URL = "http://127.0.0.1:5000/api/room-types"

room_types = [
    {
        "typeName": "Standard",
        "description": "Basic standard room with essential amenities",
        "basePrice": 2500,
        "capacity": 2
    },
    {
        "typeName": "Deluxe",
        "description": "Deluxe AC room with extra comfort",
        "basePrice": 4500,
        "capacity": 3
    },
    {
        "typeName": "Suite",
        "description": "Luxury suite room with premium facilities",
        "basePrice": 8000,
        "capacity": 5
    },
    {
        "typeName": "Family",
        "description": "Spacious room suitable for families",
        "basePrice": 6000,
        "capacity": 4
    }
]

for room_type in room_types:
    response = requests.post(BASE_URL, json=room_type)

    print(f"\nAdding Room Type: {room_type['typeName']}")
    print("Status Code:", response.status_code)

    try:
        print("Response:", response.json())
    except:
        print("Could not parse JSON response")