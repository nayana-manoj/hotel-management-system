import requests

BASE_URL = "http://127.0.0.1:5000/api/staff"

staff_members = [
    {
        "firstName": "System",
        "lastName": "Admin",
        "email": "admin@hotel.com",
        "phoneNumber": "9999999991",
        "username": "sysadmin",
        "password": "admin123",
        "role": "admin",
        "address": "Trivandrum",
        "dateOfHire": "2025-01-01",
        "salary": 75000
    },
    {
        "firstName": "Reception",
        "lastName": "Staff",
        "email": "reception@hotel.com",
        "phoneNumber": "9999999992",
        "username": "reception",
        "password": "reception123",
        "role": "receptionist",
        "address": "Kochi",
        "dateOfHire": "2025-01-01",
        "salary": 35000
    }
]

for staff in staff_members:
    response = requests.post(BASE_URL, json=staff)

    print(f"\nAdding: {staff['username']}")
    print("Status Code:", response.status_code)

    try:
        print("Response:", response.json())
    except:
        print("Could not parse JSON response")
