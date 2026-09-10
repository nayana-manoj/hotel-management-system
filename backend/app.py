import os

from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import json
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. DATABASE CONFIGURATION
# ==============================================================================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'sslmode': os.getenv('DB_SSLMODE', 'require')
}

# ==============================================================================
# 2. FLASK APPLICATION SETUP
# ==============================================================================
app = Flask(__name__)
CORS(app)

# ==============================================================================
# 3. DATABASE CONNECTION FUNCTION
# ==============================================================================


def get_db_connection():
    """Establishes a connection to the Supabase/PostgreSQL database."""
    try:
        database_url = os.getenv(
            'SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
        if database_url:
            connection = psycopg.connect(database_url, row_factory=dict_row)
        else:
            connection = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
        return connection
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None


class _PyMySQLCompat:
    # Keeps the existing except pymysql.MySQLError blocks working after the driver swap.
    MySQLError = psycopg.Error


pymysql = _PyMySQLCompat()


API_KEY_MAP = {
    'guestid': 'guestID',
    'staffid': 'staffID',
    'reservationid': 'reservationID',
    'roomtypeid': 'roomTypeID',
    'roomnumber': 'roomNumber',
    'billid': 'billID',
    'paymentid': 'paymentID',
    'serviceid': 'serviceID',
    'billserviceid': 'billServiceID',
    'firstname': 'firstName',
    'lastname': 'lastName',
    'phonenumber': 'phoneNumber',
    'idproof': 'idProof',
    'passwordhash': 'passwordHash',
    'dateofhire': 'dateOfHire',
    'checkindate': 'checkInDate',
    'checkoutdate': 'checkOutDate',
    'bookingdate': 'bookingDate',
    'numberofadults': 'numberOfAdults',
    'numberofchildren': 'numberOfChildren',
    'reservationstatus': 'reservationStatus',
    'pricepernight': 'pricePerNight',
    'typename': 'typeName',
    'baseprice': 'basePrice',
    'floornumber': 'floorNumber',
    'currentstatus': 'currentStatus',
    'billdate': 'billDate',
    'subtotal': 'subTotal',
    'taxamount': 'taxAmount',
    'totalamount': 'totalAmount',
    'paymentstatus': 'paymentStatus',
    'paymentmethod': 'paymentMethod',
    'paymentdate': 'paymentDate',
    'amountpaid': 'amountPaid',
    'transactionid': 'transactionID',
    'servicename': 'serviceName',
    'unitprice': 'unitPrice',
    'totalserviceprice': 'totalServicePrice',
    'roomtype': 'roomType'
}


def _db_row_to_api(row):
    if not row:
        return row
    return {
        API_KEY_MAP.get(key, key): value
        for key, value in row.items()
    }


def _db_rows_to_api(rows):
    return [_db_row_to_api(row) for row in rows]


def _db_get(row, api_key):
    if row is None:
        return None
    return row.get(api_key, row.get(api_key.lower()))

# ==============================================================================
# 4. API ENDPOINT FOR LOGIN
# ==============================================================================


@app.route('/api/login', methods=['POST'])
def login():
    """Authenticates a staff member and returns their role."""
    connection = None
    try:
        login_data = request.get_json()
        if not login_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        username = login_data.get('username')
        password = login_data.get('password')

        if not all([username, password]):
            return jsonify({'error': 'Missing required fields: username, password'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT staffID, username, passwordHash, role FROM staff WHERE username = %s"
            cursor.execute(sql, (username,))
            staff_member = cursor.fetchone()

            if not staff_member:
                return jsonify({'error': 'Invalid username or password'}), 401

            if check_password_hash(_db_get(staff_member, 'passwordHash'), password):
                return jsonify({
                    'message': 'Login successful!',
                    'staffID': _db_get(staff_member, 'staffID'),
                    'username': _db_get(staff_member, 'username'),
                    'role': _db_get(staff_member, 'role')
                }), 200
            else:
                return jsonify({'error': 'Invalid username or password'}), 401

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()

# ==============================================================================
# 5. API ENDPOINTS TO MANAGE GUEST DATA
# ==============================================================================


# ==============================================================================
# 5. API ENDPOINTS TO MANAGE GUEST DATA
# ==============================================================================


@app.route('/api/guests', methods=['POST'])
def add_guest():
    """Adds a new guest to the 'Guest' table."""
    connection = None
    try:
        guest_data = request.get_json()
        if not guest_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        first_name = guest_data.get('firstName')
        last_name = guest_data.get('lastName')
        email = guest_data.get('email')
        id_proof = guest_data.get('idProof')

        # --- FIX: Convert empty strings to None for optional database fields ---
        phone_number = guest_data.get('phoneNumber')
        if phone_number == "":
            phone_number = None

        address = guest_data.get('address')
        if address == "":
            address = None
        # ---------------------------------------------------------------------

        if not all([first_name, last_name, email, id_proof]):
            return jsonify({'error': 'Missing required fields: firstName, lastName, email, idProof'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO guests (firstName, lastName, email, phoneNumber, address, idProof)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING guestID
            """
            cursor.execute(sql, (first_name, last_name, email,
                                 phone_number, address, id_proof))
            new_guest_id = _db_get(cursor.fetchone(), 'guestID')
            connection.commit()

        return jsonify({
            'message': 'Guest added successfully!',
            'guestID': new_guest_id,
            'data': guest_data
        }), 201

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/guests', methods=['GET'])
def get_all_guests():
    """Retrieves and returns all guest records from the 'Guest' table."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM guests"
            cursor.execute(sql)
            guests = cursor.fetchall()

        return jsonify(_db_rows_to_api(guests)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/guests/<int:guest_id>', methods=['GET'])
def get_guest(guest_id):
    """Retrieves a single guest record by guestID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM guests WHERE guestID = %s"
            cursor.execute(sql, (guest_id,))
            guest = cursor.fetchone()

        if guest:
            return jsonify(_db_row_to_api(guest)), 200
        else:
            return jsonify({'error': 'Guest not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/guests/<int:guest_id>', methods=['PUT'])
def update_guest(guest_id):
    """Updates an existing guest record by guestID."""
    connection = None
    try:
        guest_data = request.get_json()
        if not guest_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT guestID FROM guests WHERE guestID = %s"
            cursor.execute(sql_check, (guest_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Guest not found'}), 404

            fields = []
            values = []
            for key, value in guest_data.items():
                fields.append(f"{key} = %s")
                values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(guest_id)
            sql_update = f"UPDATE guests SET {', '.join(fields)} WHERE guestID = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Guest updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/guests/<int:guest_id>', methods=['DELETE'])
def delete_guest(guest_id):
    """Deletes a guest record by guestID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT guestID FROM guests WHERE guestID = %s"
            cursor.execute(sql_check, (guest_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Guest not found'}), 404

            sql_delete = "DELETE FROM guests WHERE guestID = %s"
            cursor.execute(sql_delete, (guest_id,))
            connection.commit()

        return jsonify({'message': 'Guest deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()

# ==============================================================================
# 7. API ENDPOINTS TO MANAGE STAFF DATA
# ==============================================================================


@app.route('/api/staff', methods=['POST'])
def add_staff():
    """Adds a new staff member to the 'Staff' table with a hashed password."""
    connection = None
    try:
        staff_data = request.get_json()
        if not staff_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        first_name = staff_data.get('firstName')
        last_name = staff_data.get('lastName')
        email = staff_data.get('email')

        # --- FIX: Convert empty strings to None for optional fields ---
        phone_number = staff_data.get(
            'phoneNumber') if staff_data.get('phoneNumber') else None
        username = staff_data.get('username')
        password = staff_data.get('password')
        role = staff_data.get('role')
        address = staff_data.get(
            'address') if staff_data.get('address') else None
        date_of_hire = staff_data.get(
            'dateOfHire') if staff_data.get('dateOfHire') else None

        # Ensure salary is None if empty, then safely cast to float if present
        salary_val = staff_data.get('salary')
        salary = float(salary_val) if salary_val else None
        # -------------------------------------------------------------

        if not all([first_name, last_name, email, username, password, role]):
            return jsonify({'error': 'Missing required fields: firstName, lastName, email, username, password, role'}), 400

        password_hash = generate_password_hash(password)

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO staff (
                firstName, lastName, email, phoneNumber, username, passwordHash, role,
                address, dateOfHire, salary
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING staffID
            """
            cursor.execute(sql, (
                first_name, last_name, email, phone_number, username, password_hash, role,
                address, date_of_hire, salary
            ))
            new_staff_id = _db_get(cursor.fetchone(), 'staffID')
            connection.commit()

        return jsonify({
            'message': 'Staff member added successfully!',
            'staffID': new_staff_id
        }), 201

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/staff', methods=['GET'])
def get_all_staff():
    """Retrieves all staff records."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM staff"
            cursor.execute(sql)
            staff = cursor.fetchall()

        return jsonify(_db_rows_to_api(staff)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/staff/<int:staff_id>', methods=['GET'])
def get_staff(staff_id):
    """Retrieves a single staff record by staffID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM staff WHERE staffID = %s"
            cursor.execute(sql, (staff_id,))
            staff = cursor.fetchone()

        if staff:
            return jsonify(_db_row_to_api(staff)), 200
        else:
            return jsonify({'error': 'Staff member not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/staff/<int:staff_id>', methods=['PUT'])
def update_staff(staff_id):
    """Updates an existing staff record by staffID."""
    connection = None
    try:
        staff_data = request.get_json()
        if not staff_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT staffID FROM staff WHERE staffID = %s"
            cursor.execute(sql_check, (staff_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Staff member not found'}), 404

            fields = []
            values = []
            for key, value in staff_data.items():
                if key == 'password':
                    password_hash = generate_password_hash(value)
                    fields.append("passwordHash = %s")
                    values.append(password_hash)
                else:
                    fields.append(f"{key} = %s")
                    values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(staff_id)
            sql_update = f"UPDATE staff SET {', '.join(fields)} WHERE staffID = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Staff member updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/staff/<int:staff_id>', methods=['DELETE'])
def delete_staff(staff_id):
    """Deletes a staff record by staffID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT staffID FROM staff WHERE staffID = %s"
            cursor.execute(sql_check, (staff_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Staff member not found'}), 404

            sql_delete = "DELETE FROM staff WHERE staffID = %s"
            cursor.execute(sql_delete, (staff_id,))
            connection.commit()

        return jsonify({'message': 'Staff member deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()

# ==============================================================================
# 8. API ENDPOINTS FOR RESERVATION MANAGEMENT
# ==============================================================================


@app.route('/api/reservations', methods=['POST'])
def add_reservation():
    """Adds a new reservation to the 'Reservation' table."""
    connection = None
    try:
        reservation_data = request.get_json()
        if not reservation_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        guest_id = reservation_data.get('guestID')
        room_number = reservation_data.get('roomNumber')
        check_in_date = reservation_data.get('checkInDate')
        check_out_date = reservation_data.get('checkOutDate')

        # --- FIX: Ensure numeric fields are correctly cast and defaults are handled ---
        # Use int() and float() only if the value exists and is not empty. Default to None or 0.

        # Mandatory fields from JS form, ensure they are cast to integers
        # The form should prevent empty inputs, but casting safely prevents Python errors.
        num_adults = int(reservation_data.get('numberOfAdults') or 1)

        # Optional field (if left blank, it should be 0 or None)
        num_children_val = reservation_data.get('numberOfChildren')
        num_children = int(num_children_val) if (
            num_children_val is not None and num_children_val != "") else 0

        # Mandatory price, ensure it's cast to float
        price_per_night_val = reservation_data.get('pricePerNight')
        # If price is missing or bad, this will still throw an error, but handles empty string.
        price_per_night = float(price_per_night_val) if (
            price_per_night_val is not None and price_per_night_val != "") else 0.0

        # Date fields: ensure they are None if empty string is passed (for nullable columns)
        booking_date_val = reservation_data.get('bookingDate')
        booking_date = booking_date_val if booking_date_val else None

        status_val = reservation_data.get('reservationStatus')
        # Default to 'Pending' if not provided
        status = status_val if status_val else "Pending"
        # -----------------------------------------------------------------------------------

        if not all([guest_id, room_number, check_in_date, check_out_date]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO reservations (
                guestID, roomNumber, checkInDate, checkOutDate, bookingDate,
                numberOfAdults, numberOfChildren, reservationStatus, pricePerNight
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING reservationID
            """
            cursor.execute(sql, (
                guest_id, room_number, check_in_date, check_out_date, booking_date,
                num_adults, num_children, status, price_per_night
            ))
            new_reservation_id = _db_get(cursor.fetchone(), 'reservationID')
            connection.commit()

        return jsonify({
            'message': 'Reservation added successfully!',
            'reservationID': new_reservation_id,
            'data': reservation_data
        }), 201

    except pymysql.MySQLError as e:
        # Crucial Debug Step: This will now print the exact MySQL error to your console
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except ValueError as e:
        # Catches Python errors from bad casts (e.g., trying to int('abc'))
        print(f"Data conversion error: {e}")
        return jsonify({'error': 'Data validation failed', 'details': str(e)}), 400
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/reservations', methods=['GET'])
def get_all_reservations():
    """Retrieves all reservation records."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM reservations"
            cursor.execute(sql)
            reservations = cursor.fetchall()

        return jsonify(_db_rows_to_api(reservations)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/reservations/<int:reservation_id>', methods=['GET'])
def get_reservation(reservation_id):
    """Retrieves a single reservation record by reservationID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM reservations WHERE reservationID = %s"
            cursor.execute(sql, (reservation_id,))
            reservation = cursor.fetchone()

        if reservation:
            return jsonify(_db_row_to_api(reservation)), 200
        else:
            return jsonify({'error': 'Reservation not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/reservations/<int:reservation_id>', methods=['PUT'])
def update_reservation(reservation_id):
    """Updates an existing reservation record by reservationID."""
    connection = None
    try:
        reservation_data = request.get_json()
        if not reservation_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT reservationID FROM reservations WHERE reservationID = %s"
            cursor.execute(sql_check, (reservation_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Reservation not found'}), 404

            fields = []
            values = []
            for key, value in reservation_data.items():
                fields.append(f"{key} = %s")
                values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(reservation_id)
            sql_update = f"UPDATE reservations SET {', '.join(fields)} WHERE reservationID = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Reservation updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/reservations/<int:reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    """Deletes a reservation record by reservationID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT reservationID FROM reservations WHERE reservationID = %s"
            cursor.execute(sql_check, (reservation_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Reservation not found'}), 404

            sql_delete = "DELETE FROM reservations WHERE reservationID = %s"
            cursor.execute(sql_delete, (reservation_id,))
            connection.commit()

        return jsonify({'message': 'Reservation deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()
            connection.close()


@app.route('/api/reservations/<int:reservation_id>/status', methods=['PUT'])
def update_reservation_status(reservation_id):
    """Updates the status of an existing reservation record."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        # Read status from the request body sent by the frontend
        request_data = request.get_json()
        # Default to Checked-out if missing
        new_status = request_data.get('new_status', 'Checked-out')

        print(
            f"--- DEBUG: Attempting status update for ID {reservation_id} to '{new_status}' ---")

        with connection.cursor() as cursor:
            # Check query capitalization
            sql_check = "SELECT reservationID FROM reservations WHERE reservationID = %s"
            cursor.execute(sql_check, (reservation_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Reservation not found'}), 404

            # Check update query capitalization
            sql_update = "UPDATE reservations SET reservationStatus = %s WHERE reservationID = %s"

            # DEBUG: Print the exact values being executed
            print(
                f"Executing SQL: UPDATE reservations SET reservationStatus = '{new_status}' WHERE reservationID = {reservation_id}")

            cursor.execute(sql_update, (new_status, reservation_id))
            connection.commit()

            # Check if any rows were affected (optional but helpful for confirmation)
            if cursor.rowcount == 0:
                print(
                    f"Warning: No rows updated for reservation ID {reservation_id}. Status might already be {new_status}.")

        return jsonify({'message': f'Reservation {reservation_id} status updated to {new_status}!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()
# ==============================================================================
# 11. API ENDPOINTS FOR ROOM TYPE MANAGEMENT
# ==============================================================================


@app.route('/api/room-types', methods=['POST'])
def add_room_type():
    """Adds a new room type to the 'RoomType' table."""
    connection = None
    try:
        room_type_data = request.get_json()
        if not room_type_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        type_name = room_type_data.get('typeName')
        description = room_type_data.get('description')

        # --- FIX: Safely convert numeric fields (basePrice, capacity) ---
        base_price_val = room_type_data.get('basePrice')
        capacity_val = room_type_data.get('capacity')

        # Ensure values are converted to appropriate types, or set to None/0 if empty string,
        # otherwise a ValueError for float/int conversion will be thrown.
        base_price = float(base_price_val) if base_price_val else None
        capacity = int(capacity_val) if capacity_val else None
        # -------------------------------------------------------------

        if not all([type_name, description, base_price, capacity]):
            # This check will now correctly catch if the converted base_price or capacity is None
            return jsonify({'error': 'Missing required fields: typeName, description, basePrice, capacity'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO roomtypes (typeName, description, basePrice, capacity)
            VALUES (%s, %s, %s, %s)
            RETURNING roomTypeID
            """
            cursor.execute(sql, (type_name, description, base_price, capacity))
            new_room_type_id = _db_get(cursor.fetchone(), 'roomTypeID')
            connection.commit()

        return jsonify({
            'message': 'Room type added successfully!',
            'roomTypeID': new_room_type_id,
            'data': room_type_data
        }), 201

    except ValueError as e:
        # Catches Python errors from bad casts (e.g., trying to float('abc'))
        print(f"Data conversion error: {e}")
        return jsonify({'error': 'Data validation failed. Check if price/capacity are numeric.', 'details': str(e)}), 400
    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/room-types', methods=['GET'])
def get_all_room_types():
    """Retrieves all room type records."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM roomtypes"
            cursor.execute(sql)
            room_types = cursor.fetchall()

        return jsonify(_db_rows_to_api(room_types)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/room-types/<int:room_type_id>', methods=['GET'])
def get_room_type(room_type_id):
    """Retrieves a single room type record by roomTypeID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM roomtypes WHERE roomTypeID = %s"
            cursor.execute(sql, (room_type_id,))
            room_type = cursor.fetchone()

        if room_type:
            return jsonify(_db_row_to_api(room_type)), 200
        else:
            return jsonify({'error': 'Room type not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/room-types/<int:room_type_id>', methods=['PUT'])
def update_room_type(room_type_id):
    """Updates an existing room type record by roomTypeID."""
    connection = None
    try:
        room_type_data = request.get_json()
        if not room_type_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT roomTypeID FROM roomtypes WHERE roomTypeID = %s"
            cursor.execute(sql_check, (room_type_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Room type not found'}), 404

            fields = []
            values = []
            for key, value in room_type_data.items():
                fields.append(f"{key} = %s")
                values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(room_type_id)
            sql_update = f"UPDATE roomtypes SET {', '.join(fields)} WHERE roomTypeID = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Room type updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/room-types/<int:room_type_id>', methods=['DELETE'])
def delete_room_type(room_type_id):
    """Deletes a room type record by roomTypeID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT roomTypeID FROM roomtypes WHERE roomTypeID = %s"
            cursor.execute(sql_check, (room_type_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Room type not found'}), 404

            sql_delete = "DELETE FROM roomtypes WHERE roomTypeID = %s"
            cursor.execute(sql_delete, (room_type_id,))
            connection.commit()

        return jsonify({'message': 'Room type deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()

# ==============================================================================
# 13. API ENDPOINTS FOR ROOM MANAGEMENT
# ==============================================================================


@app.route('/api/rooms', methods=['POST'])
def add_room():
    """Adds a new room to the 'Room' table."""
    connection = None
    try:
        room_data = request.get_json()
        if not room_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        room_number = room_data.get('roomNumber')

        # --- FIX: Safely convert numeric fields (roomTypeID, floorNumber) ---
        room_type_id_val = room_data.get('roomTypeID')
        floor_number_val = room_data.get('floorNumber')

        # Convert to integer only if the value exists, otherwise None (if allowed by schema)
        # Based on the form (required: true for these), we assume they should be present.
        # We try to convert them, and let the ValueError handle bad input.
        room_type_id = int(room_type_id_val) if room_type_id_val else None
        floor_number = int(floor_number_val) if floor_number_val else None
        # -------------------------------------------------------------

        current_status = room_data.get('currentStatus')

        if not all([room_number, room_type_id, floor_number, current_status]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO rooms (roomNumber, roomTypeID, floorNumber, currentStatus)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (room_number, room_type_id,
                                 floor_number, current_status))
            connection.commit()

        return jsonify({
            'message': 'Room added successfully!',
            'roomNumber': room_number,
            'data': room_data
        }), 201

    except ValueError as e:
        # Catches Python error if roomTypeID or floorNumber cannot be converted to int
        print(f"Data conversion error: {e}")
        return jsonify({'error': 'Data validation failed. Room Type ID and Floor Number must be valid integers.', 'details': str(e)}), 400
    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/rooms', methods=['GET'])
def get_all_rooms():
    """Retrieves all room records."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM rooms"
            cursor.execute(sql)
            rooms = cursor.fetchall()

        return jsonify(_db_rows_to_api(rooms)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/rooms/<room_number>', methods=['GET'])
def get_room(room_number):
    """Retrieves a single room record by roomNumber."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM rooms WHERE roomNumber = %s"
            cursor.execute(sql, (room_number,))
            room = cursor.fetchone()

        if room:
            return jsonify(_db_row_to_api(room)), 200
        else:
            return jsonify({'error': 'Room not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/rooms-details', methods=['GET'])
def get_all_rooms_with_details():
    """
    Retrieves all room records joined with RoomType to provide the name 
    and base price for the dashboard and booking forms.
    """
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            # New query to join ROOM and ROOM_TYPE
            sql = """
            SELECT
                R.roomNumber, R.roomTypeID, R.floorNumber, R.currentStatus,
                RT.typeName AS roomType, RT.basePrice
            FROM rooms R
            JOIN roomtypes RT ON R.roomTypeID = RT.roomTypeID
            """
            cursor.execute(sql)
            rooms = cursor.fetchall()

        return jsonify(_db_rows_to_api(rooms)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/rooms/<room_number>', methods=['PUT'])
def update_room(room_number):
    """Updates an existing room record by roomNumber."""
    connection = None
    try:
        room_data = request.get_json()
        if not room_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT roomNumber FROM rooms WHERE roomNumber = %s"
            cursor.execute(sql_check, (room_number,))
            if not cursor.fetchone():
                return jsonify({'error': 'Room not found'}), 404

            fields = []
            values = []
            for key, value in room_data.items():
                fields.append(f"{key} = %s")
                values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(room_number)
            sql_update = f"UPDATE rooms SET {', '.join(fields)} WHERE roomNumber = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Room updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/rooms/<room_number>', methods=['DELETE'])
def delete_room(room_number):
    """Deletes a room record by roomNumber."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT roomNumber FROM rooms WHERE roomNumber = %s"
            cursor.execute(sql_check, (room_number,))
            if not cursor.fetchone():
                return jsonify({'error': 'Room not found'}), 404

            sql_delete = "DELETE FROM rooms WHERE roomNumber = %s"
            cursor.execute(sql_delete, (room_number,))
            connection.commit()

        return jsonify({'message': 'Room deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/rooms/available', methods=['GET'])
def get_available_rooms_by_type():
    """
    Retrieves available room numbers based on a provided roomTypeID.
    This endpoint joins the ROOM and ROOM_TYPE tables.
    Expected URL: /api/rooms/available?roomTypeId=<id>
    """
    # Use request.args.get() to safely read URL parameters
    room_type_id = request.args.get('roomTypeId')
    if not room_type_id:
        return jsonify({'error': 'Missing roomTypeId parameter.'}), 400

    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            SELECT
                R.roomNumber
            FROM
                rooms R
            JOIN
                roomtypes RT ON R.roomTypeID = RT.roomTypeID
            WHERE
                R.roomTypeID = %s AND R.currentStatus = 'Available'
            """
            cursor.execute(sql, (room_type_id,))
            available_rooms = cursor.fetchall()

        return jsonify(_db_rows_to_api(available_rooms)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error in available rooms query: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()

# ==============================================================================
# 14. API ENDPOINTS FOR BILLING MANAGEMENT
# ==============================================================================


@app.route('/api/billing', methods=['POST'])
def add_billing():
    """Adds a new bill to the 'Billing' table."""
    connection = None
    try:
        billing_data = request.get_json()
        if not billing_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        reservation_id = billing_data.get('reservationID')
        bill_date = billing_data.get('billDate')
        sub_total = billing_data.get('subTotal')
        tax_amount = billing_data.get('taxAmount')
        total_amount = billing_data.get('totalAmount')
        payment_status = billing_data.get('paymentStatus')

        if not all([reservation_id, bill_date, total_amount]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO billing (reservationID, billDate, subTotal, taxAmount, totalAmount, paymentStatus)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING billID
            """
            cursor.execute(sql, (reservation_id, bill_date,
                                 sub_total, tax_amount, total_amount, payment_status))
            new_bill_id = _db_get(cursor.fetchone(), 'billID')
            connection.commit()

        return jsonify({
            'message': 'Bill added successfully!',
            'billID': new_bill_id,
            'data': billing_data
        }), 201

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/billing', methods=['GET'])
def get_all_billing():
    """Retrieves all billing records."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM billing"
            cursor.execute(sql)
            billing_records = cursor.fetchall()

        return jsonify(_db_rows_to_api(billing_records)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/billing/<int:bill_id>', methods=['GET'])
def get_billing(bill_id):
    """Retrieves a single billing record by billID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM billing WHERE billID = %s"
            cursor.execute(sql, (bill_id,))
            billing_record = cursor.fetchone()

        if billing_record:
            return jsonify(_db_row_to_api(billing_record)), 200
        else:
            return jsonify({'error': 'Bill not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/billing/<int:bill_id>', methods=['PUT'])
def update_billing(bill_id):
    """Updates an existing billing record by billID."""
    connection = None
    try:
        billing_data = request.get_json()
        if not billing_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT billID FROM billing WHERE billID = %s"
            cursor.execute(sql_check, (bill_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Bill not found'}), 404

            fields = []
            values = []
            for key, value in billing_data.items():
                fields.append(f"{key} = %s")
                values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(bill_id)
            sql_update = f"UPDATE billing SET {', '.join(fields)} WHERE billID = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Bill updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/billing/<int:bill_id>', methods=['DELETE'])
def delete_billing(bill_id):
    """Deletes a billing record by billID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT billID FROM billing WHERE billID = %s"
            cursor.execute(sql_check, (bill_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Bill not found'}), 404

            sql_delete = "DELETE FROM billing WHERE billID = %s"
            cursor.execute(sql_delete, (bill_id,))
            connection.commit()

        return jsonify({'message': 'Bill deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()

# ==============================================================================
# 15. API ENDPOINTS FOR PAYMENT MANAGEMENT
# ==============================================================================


@app.route('/api/payments', methods=['POST'])
def add_payment():
    """Adds a new payment to the 'Payment' table."""
    connection = None
    try:
        payment_data = request.get_json()
        if not payment_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        bill_id = payment_data.get('billID')
        payment_method = payment_data.get('paymentMethod')
        payment_date = payment_data.get('paymentDate')
        amount_paid = payment_data.get('amountPaid')
        transaction_id = payment_data.get('transactionID')

        if not all([bill_id, payment_method, payment_date, amount_paid]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO payments (billID, paymentMethod, paymentDate, amountPaid, transactionID)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING paymentID
            """
            cursor.execute(sql, (bill_id, payment_method,
                                 payment_date, amount_paid, transaction_id))
            new_payment_id = _db_get(cursor.fetchone(), 'paymentID')
            connection.commit()

        return jsonify({
            'message': 'Payment added successfully!',
            'paymentID': new_payment_id,
            'data': payment_data
        }), 201

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/payments', methods=['GET'])
def get_all_payments():
    """Retrieves all payment records."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM payments"
            cursor.execute(sql)
            payments = cursor.fetchall()

        return jsonify(_db_rows_to_api(payments)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/payments/<int:payment_id>', methods=['GET'])
def get_payment(payment_id):
    """Retrieves a single payment record by paymentID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM payments WHERE paymentID = %s"
            cursor.execute(sql, (payment_id,))
            payment = cursor.fetchone()

        if payment:
            return jsonify(_db_row_to_api(payment)), 200
        else:
            return jsonify({'error': 'Payment not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/payments/<int:payment_id>', methods=['PUT'])
def update_payment(payment_id):
    """Updates an existing payment record by paymentID."""
    connection = None
    try:
        payment_data = request.get_json()
        if not payment_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT paymentID FROM payments WHERE paymentID = %s"
            cursor.execute(sql_check, (payment_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Payment not found'}), 404

            fields = []
            values = []
            for key, value in payment_data.items():
                fields.append(f"{key} = %s")
                values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(payment_id)
            sql_update = f"UPDATE payments SET {', '.join(fields)} WHERE paymentID = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Payment updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/payments/<int:payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    """Deletes a payment record by paymentID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT paymentID FROM payments WHERE paymentID = %s"
            cursor.execute(sql_check, (payment_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Payment not found'}), 404

            sql_delete = "DELETE FROM payments WHERE paymentID = %s"
            cursor.execute(sql_delete, (payment_id,))
            connection.commit()

        return jsonify({'message': 'Payment deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()

# ==============================================================================
# 16. API ENDPOINTS FOR SERVICE MANAGEMENT
# ==============================================================================


@app.route('/api/services', methods=['POST'])
def add_service():
    """Adds a new service to the 'Service' table."""
    connection = None
    try:
        service_data = request.get_json()
        if not service_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        service_name = service_data.get('serviceName')

        # --- FIX 1: Handle optional field (description) as None if empty string ---
        description_val = service_data.get('description')
        description = description_val if description_val else None

        # --- FIX 2: Safely convert unitPrice to float, handle empty string ---
        unit_price_val = service_data.get('unitPrice')
        unit_price = float(unit_price_val) if unit_price_val else None
        # -----------------------------------------------------------------------

        if not all([service_name, unit_price]):
            # This check now correctly catches if unit_price conversion failed or was missing
            return jsonify({'error': 'Missing required fields: serviceName, unitPrice'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO services (serviceName, description, unitPrice)
            VALUES (%s, %s, %s)
            RETURNING serviceID
            """
            cursor.execute(sql, (service_name, description, unit_price))
            new_service_id = _db_get(cursor.fetchone(), 'serviceID')
            connection.commit()

        return jsonify({
            'message': 'Service added successfully!',
            'serviceID': new_service_id,
            'data': service_data
        }), 201

    except ValueError as e:
        # Catches Python error if unitPrice cannot be converted to float
        print(f"Data conversion error: {e}")
        return jsonify({'error': 'Data validation failed. Unit Price must be a valid number.', 'details': str(e)}), 400
    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/services', methods=['GET'])
def get_all_services():
    """Retrieves all service records."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM services"
            cursor.execute(sql)
            services = cursor.fetchall()

        return jsonify(_db_rows_to_api(services)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/services/<int:service_id>', methods=['GET'])
def get_service(service_id):
    """Retrieves a single service record by serviceID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM services WHERE serviceID = %s"
            cursor.execute(sql, (service_id,))
            service = cursor.fetchone()

        if service:
            return jsonify(_db_row_to_api(service)), 200
        else:
            return jsonify({'error': 'Service not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/services/<int:service_id>', methods=['PUT'])
def update_service(service_id):
    """Updates an existing service record by serviceID."""
    connection = None
    try:
        service_data = request.get_json()
        if not service_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT serviceID FROM services WHERE serviceID = %s"
            cursor.execute(sql_check, (service_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Service not found'}), 404

            fields = []
            values = []
            for key, value in service_data.items():
                fields.append(f"{key} = %s")
                values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(service_id)
            sql_update = f"UPDATE services SET {', '.join(fields)} WHERE serviceID = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Service updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/services/<int:service_id>', methods=['DELETE'])
def delete_service(service_id):
    """Deletes a service record by serviceID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT serviceID FROM services WHERE serviceID = %s"
            cursor.execute(sql_check, (service_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Service not found'}), 404

            sql_delete = "DELETE FROM services WHERE serviceID = %s"
            cursor.execute(sql_delete, (service_id,))
            connection.commit()

        return jsonify({'message': 'Service deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()

# ==============================================================================
# 17. API ENDPOINTS FOR BILL_SERVICE MANAGEMENT
# ==============================================================================


@app.route('/api/bill-services', methods=['POST'])
def add_bill_service():
    """Adds a new record to the 'Bill_Service' junction table."""
    connection = None
    try:
        bill_service_data = request.get_json()
        if not bill_service_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        bill_id = bill_service_data.get('billID')
        service_id = bill_service_data.get('serviceID')
        quantity = bill_service_data.get('quantity')
        total_service_price = bill_service_data.get('totalServicePrice')

        if not all([bill_id, service_id, quantity]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO billservices (billID, serviceID, quantity, totalServicePrice)
            VALUES (%s, %s, %s, %s)
            RETURNING billServiceID
            """
            cursor.execute(sql, (bill_id, service_id,
                                 quantity, total_service_price))
            new_bill_service_id = _db_get(cursor.fetchone(), 'billServiceID')
            connection.commit()

        return jsonify({
            'message': 'Bill service added successfully!',
            'billServiceID': new_bill_service_id,
            'data': bill_service_data
        }), 201

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/bill-services', methods=['GET'])
def get_all_bill_services():
    """Retrieves all bill_service records."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM billservices"
            cursor.execute(sql)
            bill_services = cursor.fetchall()

        return jsonify(_db_rows_to_api(bill_services)), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/bill-services/<int:bill_service_id>', methods=['GET'])
def get_bill_service(bill_service_id):
    """Retrieves a single bill_service record by billServiceID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql = "SELECT * FROM billservices WHERE billServiceID = %s"
            cursor.execute(sql, (bill_service_id,))
            bill_service = cursor.fetchone()

        if bill_service:
            return jsonify(_db_row_to_api(bill_service)), 200
        else:
            return jsonify({'error': 'Bill service record not found'}), 404

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/bill-services/<int:bill_service_id>', methods=['PUT'])
def update_bill_service(bill_service_id):
    """Updates an existing bill_service record by billServiceID."""
    connection = None
    try:
        bill_service_data = request.get_json()
        if not bill_service_data:
            return jsonify({'error': 'Invalid JSON data provided.'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT billServiceID FROM billservices WHERE billServiceID = %s"
            cursor.execute(sql_check, (bill_service_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Bill service record not found'}), 404

            fields = []
            values = []
            for key, value in bill_service_data.items():
                fields.append(f"{key} = %s")
                values.append(value)

            if not fields:
                return jsonify({'message': 'No fields to update.'}), 200

            values.append(bill_service_id)
            sql_update = f"UPDATE billservices SET {', '.join(fields)} WHERE billServiceID = %s"

            cursor.execute(sql_update, tuple(values))
            connection.commit()

        return jsonify({'message': 'Bill service record updated successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/bill-services/<int:bill_service_id>', methods=['DELETE'])
def delete_bill_service(bill_service_id):
    """Deletes a bill_service record by billServiceID."""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed.'}), 500

        with connection.cursor() as cursor:
            sql_check = "SELECT billServiceID FROM billservices WHERE billServiceID = %s"
            cursor.execute(sql_check, (bill_service_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Bill service record not found'}), 404

            sql_delete = "DELETE FROM billservices WHERE billServiceID = %s"
            cursor.execute(sql_delete, (bill_service_id,))
            connection.commit()

        return jsonify({'message': 'Bill service record deleted successfully!'}), 200

    except pymysql.MySQLError as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
    finally:
        if connection:
            connection.close()


# ==============================================================================
# 18. RUN THE FLASK APPLICATION
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
