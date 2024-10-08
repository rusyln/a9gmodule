import subprocess
import time

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
    print(f"Running command: {command}")
    process.stdin.write(command + '\n')
    process.stdin.flush()
    time.sleep(1)  # Allow some time for processing

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
        print("Waiting for a device to connect...")
        start_time = time.time()
        authorized_service_found = False

        while True:
            # Read output continuously
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break  # Exit loop if the process is terminated
            if output:
                print(f"Output: {output.strip()}")

                # Check for the passkey confirmation prompt
                if "Confirm passkey" in output:
                    print("Responding 'yes' to passkey confirmation...")
                    run_command(process, "yes")

                # Check for authorization service prompt
                if "[agent] Authorize service" in output:
                    print("Responding 'yes' to authorization service...")
                    run_command(process, "yes")
                    authorized_service_found = True  # Set flag if service is authorized

                # Reset the timer if any expected output is found
                if authorized_service_found:
                    start_time = time.time()

            # Check if 10 seconds have passed without seeing the authorization prompt
            if time.time() - start_time > 10 and not authorized_service_found:
                print("No authorization service found within 10 seconds. Sending 'quit' command to bluetoothctl...")
                run_command(process, "quit")
                start_time = time.time()  # Reset the timer after sending quit

    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        # Stop scanning
        print("Stopping device discovery...")
        run_command(process, "scan off")
        process.terminate()

if __name__ == "__main__":
    main()
