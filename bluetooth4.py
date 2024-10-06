import bluetooth
import subprocess

# Create a Bluetooth socket
server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

# Use bluetooth.PORT_ANY to let the OS choose an available port
port = 23
server_sock.bind(("", port))
server_sock.listen(1)

print(f"Listening for connections on RFCOMM channel {port}...")

try:
    client_sock, address = server_sock.accept()
    print("Connection established with:", address)

    while True:
        recvdata = client_sock.recv(1024).decode('utf-8').strip()  # Decode bytes to string and strip whitespace
        print("Received command:", recvdata)
        
        if recvdata == "Q":
            print("Ending connection.")
            break
        
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

