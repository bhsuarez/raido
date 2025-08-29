#!/usr/bin/env python3

import socket
import sys

def test_liquidsoap():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("localhost", 1234))
        
        # Send help command
        sock.send(b"help\n")
        
        # Read response
        response = sock.recv(8192).decode()
        print("=== LIQUIDSOAP HELP ===")
        print(response)
        print("=== END HELP ===\n")
        
        # Try some other commands
        commands = ["version", "exit"]  # exit to close connection cleanly
        
        for cmd in commands:
            try:
                sock.send(f"{cmd}\n".encode())
                response = sock.recv(2048).decode().strip()
                print(f"{cmd}: {response}")
                if cmd == "exit":
                    break
            except:
                break
        
        sock.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_liquidsoap()