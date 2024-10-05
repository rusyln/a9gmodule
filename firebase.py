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

def convert_to_decimal_degrees(coord):
    """Convert NMEA format coordinate to decimal degrees."""
    degrees = int(coord[:2])  # Degrees
    minutes = float(coord[2:])  # Minutes
    decimal_degrees = degrees + (minutes / 60)  # Convert to decimal degrees
    return round(decimal_degrees, 7)  # Round to 7 decimal places

def get_gps_location():
    """Fetch GPS location data from the A9G module and convert to decimal degrees."""
    
    # Check if GPS is already enabled
    gps_status_response = send_command('AT+GPS=1')  # Check GPS status
    print("GPS Status Response:", gps_status_response)  # Log the response

    # If GPS is not enabled, enable it
    if "OK" not in gps_status_response:  # Check for "OK" in response to confirm GPS is enabled
        gps_enable_response = send_command('AT+GPS=1')  # Activate GPS
        print("GPS Activation Response:", gps_enable_response)  # Log the response

    # Wait a moment to allow GPS to acquire a signal
    time.sleep(12)  # Wait for 12 seconds before reading GPS data

    # Read GPS data
    response = send_command('AT+GPSRD=5')  # Read GPS data
    print("GPS Data Read Response:", response)  # Log GPS data read response

    time.sleep(12)
    latitude, longitude = None, None
    
    # Process the response to find GNGGA sentence
    for line in response:
        # Check if the line is in bytes and decode if necessary
        if isinstance(line, bytes):
            line = line.decode().strip()  # Decode only if it's bytes
        else:
            line = line.strip()  # Strip any whitespace if it's already a string

        # Check for GNGGA sentence
        if "$GNGGA" in line:
            print(f"Found GNGGA Line: {line}")  # Log found GNGGA line
            
            parts = line.split(",")
            if len(parts) > 6:  # Check if we have enough data
                latitude = convert_to_decimal_degrees(parts[2])  # Latitude in NMEA format
                longitude = convert_to_decimal_degrees(parts[4])  # Longitude in NMEA format
                
                # Adjust signs based on hemisphere indicators
                if parts[3] == 'S':
                    latitude = -latitude
                if parts[5] == 'W':
                    longitude = -longitude
                
                print(f"Latitude: {latitude}, Longitude: {longitude}")  # Log the values
                break  # Exit after processing the first GNGGA sentence

    # Stop reading GPS data
    send_command('AT+GPSRD=0')  # Stop GPS data reading
    print("Stopped GPS Data Reading.")  # Log that reading has stopped

    if latitude is None or longitude is None:
        print("No valid GPS data found.")
    
    return latitude, longitude

def convert_to_decimal_degrees(coord):
    """Convert NMEA format coordinate to decimal degrees."""
    degrees = int(coord[:2])  # Degrees
    minutes = float(coord[2:])  # Minutes
    return degrees + (minutes / 60)  # Convert to decimal degrees


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

def send_to_firebase(latitude, longitude):
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

        # Push data to Firebase
        db.child("locations").push(data)
        print(f"Sent to Firebase: {data}")
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
    """Triggered when the button is held for 3 seconds."""
    print("Button held for 3 seconds! Fetching GPS location...")
    latitude, longitude = get_gps_location()
    
    if latitude and longitude:
        save_location_to_file(latitude, longitude)
        
        # Send the location data to Firebase
        send_to_firebase(latitude, longitude)

        # Send SMS with latitude and longitude to all contacts
        send_sms_to_all_contacts(latitude, longitude)
        print("SMS sent to all contacts.")

    else:
        print("No GPS data received.")

    # Delay before returning to waiting for button press
    time.sleep(3)
    print("Returning to waiting for button press...")


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
