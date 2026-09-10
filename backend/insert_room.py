import requests

BASE_URL = "http://127.0.0.1:5000/api/rooms"

rooms = [
    {
        "roomNumber": 101,
        "roomTypeID": 1,
        "floorNumber": 1,
        "currentStatus": "Available"
    },
    {
        "roomNumber": 102,
        "roomTypeID": 1,
        "floorNumber": 1,
        "currentStatus": "Occupied"
    },
    {
        "roomNumber": 201,
        "roomTypeID": 2,
        "floorNumber": 2,
        "currentStatus": "Available"
    },
    {
        "roomNumber": 202,
        "roomTypeID": 2,
        "floorNumber": 2,
        "currentStatus": "Maintenance"
    },
    {
        "roomNumber": 301,
        "roomTypeID": 3,
        "floorNumber": 3,
        "currentStatus": "Available"
    }
]

for room in rooms:
    response = requests.post(BASE_URL, json=room)

    print(f"\nAdding Room: {room['roomNumber']}")
    print("Status Code:", response.status_code)

    try:
        print("Response:", response.json())
    except:
        print("Could not parse JSON response")