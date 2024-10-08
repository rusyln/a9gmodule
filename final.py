import subprocess
import time
import sys
import bluetooth  # Ensure you have pybluez installed to use this library
import RPi.GPIO as GPIO  # Import RPi.GPIO library

# Set up GPIO pins
GREEN_LED_PIN = 18  # GPIO pin for the green LED
ORANGE_LED_PIN = 23  # GPIO pin for the orange LED
BUTTON_PIN_1 = 17  # GPIO pin for the standby button
BUTTON_PIN_2 = 27  # GPIO pin for the Bluetooth command button

GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
GPIO.setup(GREEN_LED_PIN, GPIO.OUT)  # Set green LED pin as an output
GPIO.setup(ORANGE_LED_PIN, GPIO.OUT)  # Set orange LED pin as an output
GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Set button 1 pin as input with pull-up resistor
GPIO.setup(BUTTON_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Set button 2 pin as input with pull-up resistor

def run_bluetoothctl():
    """Start bluetoothctl as a subprocess and return the process handle."""
    return subprocess.Popen(
        ['bluetoothctl'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line-buffered
    )

def run_command(process, command):
    """Run a command in bluetoothctl."""
    if process.poll() is None:  # Check if the process is still running
        print(f"Running command: {command}")
        process.stdin.write(command + '\n')
        process.stdin.flush()
        time.sleep(1)  # Allow some time for processing
    else:
        print(f"Process is not running. Unable to execute command: {command}")

def start_rfcomm_server():
    """Start RFCOMM server on channel 23."""
    print("Starting RFCOMM server on channel 23...")

    # Create a Bluetooth socket
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    port = 24
    server_sock.bind(("", port))
    server_sock.listen(1)

    print(f"Listening for connections on RFCOMM channel {port}...")

    try:
        client_sock, address = server_sock.accept()
        print("Connection established with:", address)
        GPIO.output(GREEN_LED_PIN, GPIO.LOW)  # Turn off the green LED when connected
        GPIO.output(ORANGE_LED_PIN, GPIO.HIGH)  # Turn on the orange LED when connected

        while True:
            recvdata = client_sock.recv(1024).decode('utf-8').strip()  # Decode bytes to string and strip whitespace
            print("Received command:", recvdata)

            if recvdata == "Q":
                print("Ending connection.")
                break
            if recvdata == "socket close":
                print("Ending connection.")
                server_sock.close()
                break   

            if recvdata == "stop led":
                print("Turning off the LED.")
                GPIO.output(GREEN_LED_PIN, GPIO.LOW)  # Turn off the green LED
                continue

            # Execute the received command
            try:
                # Run the command using subprocess
                output = subprocess.check_output(recvdata, shell=True, text=True)
                print("Command output:", output)  # Print command output for debugging
                client_sock.send(output.encode('utf-8'))  # Send the output back to the client
            except subprocess.CalledProcessError as e:
                error_message = f"Error executing command: {e}\nOutput: {e.output}"
                print("Error:", error_message)  # Print the error for debugging
                client_sock.send(error_message.encode('utf-8'))  # Send error message back to client

    except OSError as e:
        print("Error:", e)

    finally:
        client_sock.close()
        server_sock.close()
        print("Sockets closed.")

def run_raspberry_pi_command(command):
    """Run a command on Raspberry Pi."""
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        print("Command output:", output)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}\nOutput: {e.output}")

def main():
    # Start bluetoothctl
    process = run_bluetoothctl()

    # Power on the Bluetooth adapter
    print("Powering on the Bluetooth adapter...")
    run_command(process, "power on")

    # Make the device discoverable
    print("Making device discoverable...")
    run_command(process, "discoverable on")

    # Enable the agent
    print("Enabling agent...")
    run_command(process, "agent on")

    # Set as default agent
    print("Setting default agent...")
    run_command(process, "default-agent")

    # Start device discovery
    print("Starting device discovery...")
    run_command(process, "scan on")

    try:
        print("Waiting for button presses...")
        GPIO.output(GREEN_LED_PIN, GPIO.HIGH)  # Turn on the green LED while waiting

        while True:
            button1_state = GPIO.input(BUTTON_PIN_1)  # Read state of button 1
            button2_state = GPIO.input(BUTTON_PIN_2)  # Read state of button 2
            
            if button2_state == GPIO.LOW:  # If button 2 is pressed
                GPIO.output(GREEN_LED_PIN, GPIO.LOW)  # Turn off green LED
                GPIO.output(ORANGE_LED_PIN, GPIO.HIGH)  # Turn on orange LED
                print("Button 2 pressed, starting Bluetooth connection...")
                start_rfcomm_server()  # Start the Bluetooth server
                GPIO.output(ORANGE_LED_PIN, GPIO.LOW)  # Turn off orange LED after connection
                GPIO.output(GREEN_LED_PIN, GPIO.HIGH)  # Turn on green LED again
                time.sleep(1)  # Debounce delay after connection
            elif button1_state == GPIO.LOW:  # If button 1 is pressed
                print("Button 1 pressed, going to standby mode.")
                # In standby mode, do nothing or wait for the button to be released
                while GPIO.input(BUTTON_PIN_1) == GPIO.LOW:
                    time.sleep(0.1)  # Wait for button release
            else:
                time.sleep(0.1)  # Wait before checking button states again

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        # Cleanup GPIO settings
        GPIO.cleanup()
        
        # Stop scanning if bluetoothctl is still running
        if process.poll() is None:
            print("\nStopping device discovery...")
            run_command(process, "scan off")
        else:
            print("\nbluetoothctl has already exited.")

        process.terminate()

if __name__ == "__main__":
    main()
