import serial
import time
import pyrebase
import os
from gpiozero import Button
from signal import pause

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
    """Get the GPS location from the A9G module."""
    response = send_command('AT+LOCATION=2')
    print("GPS Location Response:", response)
    for line in response:
        # Check if the line contains GPS data (not empty and not the 'OK' response)
        if line and "OK" not in line:
            try:
                # Split the line into latitude and longitude
                location_data = line.split(",")
                if len(location_data) >= 2:  # Ensure there are at least 2 values
                    latitude = location_data[0].strip()  # First part is latitude
                    longitude = location_data[1].strip()  # Second part is longitude
                    return latitude, longitude
            except IndexError:
                print("Error parsing GPS data.")
                return None, None
    return None, None

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
    """Send latitude and longitude to Firebase Realtime Database."""
    if check_firebase_connection():
        data = {
            "latitude": latitude,
            "longitude": longitude
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

def on_button_held():
    """Triggered when the button is held for 3 seconds."""
    print("Button held for 3 seconds! Fetching GPS location...")
    latitude, longitude = get_gps_location()
    if latitude and longitude:
        save_location_to_file(latitude, longitude)
        # Now retrieve and send the location data to Firebase
        latitude, longitude = read_location_from_file()
        if latitude and longitude:
            send_to_firebase(latitude, longitude)
    else:
        print("No GPS data received.")

def main():
    """Main function to run the script."""
    if not check_module_ready():
        print("A9G module is not ready.")
        return

    # Authenticate with Firebase
    try:
        user = auth.sign_in_with_email_and_password("your_email@example.com", "your_password")
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
