import subprocess
import threading
import re
import bluetooth
import time

# Global variable to store the last connected MAC address
last_connected_mac = None

def auto_accept_pairing():
    global last_connected_mac
    
    print("Listening for pairing requests...")
    process = subprocess.Popen(['bluetoothctl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        while True:
            output = process.stdout.readline()
            if output:
                output = output.strip()
                print(output)

                device_match = re.search(r'Device\s+([0-9A-Fa-f:]{17})', output)
                if device_match:
                    mac_address = device_match.group(1)
                    print(f"Connected device MAC address: {mac_address}")
                    
                    # Check if it's the same device as before
                    if mac_address == last_connected_mac:
                        print("Same device detected. Ignoring.")
                        continue  # Skip saving and proceed to handle other prompts

                    # Save the MAC address if it's different
                    print(f"Saving MAC address: {mac_address}")
                    save_mac_address(mac_address)
                    last_connected_mac = mac_address  # Update last connected MAC
                    
                    # Automatically confirm the passkey and authorize service
                    print("Automatically confirming the passkey...")
                    process.stdin.write('yes\n')
                    process.stdin.flush()
                    
                    time.sleep(1)
                    print("Authorization request received. Automatically authorizing service...")
                    process.stdin.write('yes\n')
                    process.stdin.flush()

                    time.sleep(1)
                    print("Quitting bluetoothctl after authorization...")
                    process.stdin.write('quit\n')
                    time.sleep(1)
                    process.stdin.flush()
                    break

                elif 'Request confirmation' in output or 'Confirm passkey' in output:
                    print("Automatically confirming the passkey...")
                    process.stdin.write('yes\n')
                    process.stdin.flush()

                elif 'Authorize service' in output:
                    print("Authorization request received. Automatically authorizing service...")
                    process.stdin.write('yes\n')
                    process.stdin.flush()
                    time.sleep(1)

                elif 'Invalid command' in output:
                    print("Invalid command detected. Quitting bluetoothctl...")
                    process.stdin.write('quit\n')
                    process.stdin.flush()
                    break

                if 'Paired: yes' in output or 'Connection successful' in output:
                    print("Pairing completed successfully.")
                    process.terminate()
                    break

    except KeyboardInterrupt:
        print("Exiting...")
        process.terminate()

def save_mac_address(mac_address):
    with open('device_connected.txt', 'a') as file:
        file.write(f"{mac_address}\n")
    print(f"Saved MAC address: {mac_address} to device_connected.txt")

# Start Bluetooth and listen for pairing requests
def enable_bluetooth():
    print("Enabling Bluetooth...")
    subprocess.run(["bluetoothctl", "power", "on"])
    subprocess.run(["bluetoothctl", "discoverable", "on"])
    subprocess.run(["bluetoothctl", "pairable", "on"])
    print("Bluetooth is enabled, discoverable, and pairable.")
    
    threading.Thread(target=auto_accept_pairing, daemon=True).start()

# Start waiting for pairing completion
def wait_for_pairing_completion():
    print("Waiting for pairing to complete...")
    while not last_connected_mac:
        time.sleep(1)
    print("Pairing completed. Proceeding with SP service setup and RFCOMM server...")
    start_rfcomm_server()

def start_rfcomm_server():
    print("Starting RFCOMM server on channel 23...")
    subprocess.run(["sudo", "sdptool", "add", "--channel=23", "SP"])
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    port = 23
    server_sock.bind(("", port))
    server_sock.listen(1)
    print(f"Listening for connections on RFCOMM channel {port}...")

    try:
        client_sock, address = server_sock.accept()
        print("Connection established with:", address)

        while True:
            recvdata = client_sock.recv(1024).decode('utf-8').strip()
            print("Received command:", recvdata)

            if recvdata == "Q":
                print("Ending connection.")
                break

            try:
                output = subprocess.check_output(recvdata, shell=True, text=True)
                print("Command output:", output)
                client_sock.send(output.encode('utf-8'))
            except subprocess.CalledProcessError as e:
                error_message = f"Error executing command: {e}\nOutput: {e.output}"
                print("Error:", error_message)
                client_sock.send(error_message.encode('utf-8'))

    except OSError as e:
        print("Error:", e)

    finally:
        client_sock.close()
        server_sock.close()
        print("Sockets closed.")

# Initialize the button
BUTTON_PIN = 17
button = Button(BUTTON_PIN)
button.when_held = enable_bluetooth

print("Waiting for button press...")
threading.Thread(target=wait_for_pairing_completion, daemon=True).start()
