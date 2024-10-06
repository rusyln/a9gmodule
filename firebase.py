import serial
import time
import pyrebase
import os
from gpiozero import Button
from signal import pause
from datetime import datetime

# Firebase configuration
firebase_config = {
    "apiKey": "AIzaSyDDSdaUY3Jf69ptM0jyHq150x_F10tBFuY",
    "authDomain": "citysafe-8b072.firebaseapp.com",
    "projectId": "citysafe-8b072",
    "databaseURL": "https://citysafe-8b072-default-rtdb.asia-southeast1.firebasedatabase.app",
    "storageBucket": "citysafe-8b072.appspot.com",
}

# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()  # Add this line for authentication
db = firebase.database()

# Initialize Serial connection with A9G module
ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

# Specify the path for the GPS location file
gps_location_file_path = os.path.join(os.getcwd(), 'GPS_location.txt')

# Define the button GPIO pin (GPIO17)
button_pin = 17
button = Button(button_pin, hold_time=3)  # Set hold time to 3 seconds

def send_command(command):
    """Send a command to the A9G module and return the response."""
    ser.write((command + '\r\n').encode())
    time.sleep(1)  # Wait for the response
    response = ser.readlines()
    return [line.decode('utf-8').strip() for line in response]

def check_module_ready():
    """Check if the A9G module is ready by sending the AT command."""
    response = send_command('AT')
    print("AT Command Response:", response)
    return any("OK" in line for line in response)

def get_gps_location():
    """Fetch GPS location data from the A9G module using AT+LOCATION=2."""
    # Enable GPS if it's not enabled
    gps_enable_response = send_command('AT+GPS=1')  # Ensure GPS is enabled
    print("GPS Activation Response:", gps_enable_response)

    # Request GPS data for 5 seconds
    gps_read_response = send_command('AT+GPSRD=5')
    print("GPS Read Response:", gps_read_response)

    # Wait for a moment to ensure data is ready
    time.sleep(6)  # Wait for 5 seconds to allow GPS to gather data

    # Now request GPS location
    response = send_command('AT+LOCATION=2')
    print("GPS Location Response:", response)

    latitude, longitude = None, None

    # Check for the expected response format
    for line in response:
        if "OK" not in line and line:  # Exclude the OK line
            try:
                latitude, longitude = map(float, line.split(','))
                print(f"Latitude: {latitude}, Longitude: {longitude}")
                break  # Exit once valid data is found
            except ValueError:
                print(f"Failed to parse GPS data: {line}")

    # Instead of stopping GPS, we just read the data again for 5 seconds
    gps_read_response = send_command('AT+GPSRD=0')
    print("GPS Read Response After Location Request:", gps_read_response)

    if latitude is None or longitude is None:
        print("No valid GPS data found.")
    
    return latitude, longitude
def save_location_to_file(latitude, longitude):
    """Save latitude and longitude to a file."""
    with open(gps_location_file_path, 'w') as f:
        f.write(f"{latitude},{longitude}")
    print(f"Saved to {gps_location_file_path}: {latitude},{longitude}")

def read_location_from_file():
    """Read latitude and longitude from the file."""
    try:
        with open(gps_location_file_path, 'r') as f:
            location_data = f.readline().strip()
            latitude, longitude = location_data.split(',')
            return latitude, longitude
    except FileNotFoundError:
        print("GPS_location.txt not found.")
        return None, None

def send_to_firebase(user_id, latitude, longitude):
    """Send latitude and longitude to Firebase Realtime Database along with device ID and timestamp."""
    if check_firebase_connection():
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get current date and time
        device_id = "citysafe01"  # Device ID

        data = {
            "latitude": latitude,
            "longitude": longitude,
            "device_id": device_id,
            "timestamp": current_time  # Current date and time
        }

        # Update the location entry for the given user ID
        db.child("locations").child(user_id).update(data)
        print(f"Updated location in Firebase for user {user_id}: {data}")
    else:
        print("Unable to connect to Firebase.")



def check_firebase_connection():
    """Check if we can connect to Firebase by attempting to read a value."""
    try:
        # Try to read a value from Firebase
        db.child("locations").get()
        print("Firebase connection successful.")
        return True
    except Exception as e:
        print(f"Firebase connection error: {e}")
        return False

def read_contacts_from_file():
    """Read contacts from a file and return them as a list."""
    try:
        with open("Contacts.txt", "r") as file:
            contacts = [line.strip() for line in file if line.strip()]  # Read and strip lines
        return contacts
    except Exception as e:
        print(f"Error reading contacts: {e}")
        return []

def send_sms(latitude, longitude, contact):
    """Send an SMS with the latitude and longitude using the A9G module."""
    # Prepare the message body with latitude and longitude
    message_body = f"{latitude},{longitude}"

    # Set SMS format to text mode
    response = send_command('AT+CMGF=1')
    print("Setting SMS format:", response)

    # Prepare the SMS command
    sms_command = f'AT+CMGS="{contact}"'  # Send to the contact in the loop
    response = send_command(sms_command)
    print("SMS Command Response:", response)

    # Send the message body
    ser.write((message_body + chr(26)).encode())  # Send the message followed by Ctrl+Z (ASCII 26)
    time.sleep(3)  # Wait for the message to be sent

    # Check for response
    response = ser.readlines()
    print("SMS Response:", response)

def send_sms_to_all_contacts(latitude, longitude):
    """Send SMS with latitude and longitude to all contacts from the Contacts.txt file."""
    contacts = read_contacts_from_file()
    
    if not contacts:
        print("No contacts to send SMS.")
        return

    for contact in contacts:
        print(f"Sending SMS to {contact}...")
        send_sms(latitude, longitude, contact)  # Send to each contact
        time.sleep(1)  # Delay to avoid overwhelming the module

def on_button_held():
    print("Button held for 3 seconds! Fetching GPS location...")
    latitude, longitude = get_gps_location()  # Fetch GPS location
    if latitude is not None and longitude is not None:
        save_location_to_file(latitude, longitude)
        user_id = "example_user_id"  # Replace with the actual user ID
        send_to_firebase(user_id, latitude, longitude)  # Pass latitude and longitude here
# Send SMS with latitude and longitude to all contacts
        send_sms_to_all_contacts(latitude, longitude)
        print("SMS sent to all contacts.")
    else:
        print("Failed to retrieve GPS location.")

# Connect the button callback to the hold event
button.when_held = on_button_held

def main():
    """Main function to run the script."""
    if not check_module_ready():
        print("A9G module is not ready.")
        return

    # Get credentials from environment variables
    email = os.getenv('FIREBASE_EMAIL')
    password = os.getenv('FIREBASE_PASSWORD')

    # Authenticate with Firebase
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        print("Authenticated successfully.")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # Assign the function to be called when the button is held for 3 seconds
    button.when_held = on_button_held

    # Keep the script running to detect button presses and holds
    print("Waiting for button press...")
    pause()  # Pause the script to keep it running

if __name__ == "__main__":
    main()
