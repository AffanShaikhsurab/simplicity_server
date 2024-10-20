import os
import subprocess
import time
import re
import signal
import sys

def cleanup(tunnel_process, flask_process):
    print("Cleaning up...")
    if tunnel_process:
        tunnel_process.terminate()
    if flask_process:
        flask_process.terminate()
    sys.exit(0)

def main():
    tunnel_process = None
    flask_process = None

    try:
        # Start Cloudflare tunnel
        print("Starting Cloudflare tunnel...")
        tunnel_process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', 'http://localhost:5000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        # Wait for the tunnel URL to appear in the output
        tunnel_url = None
        while True:
            output = tunnel_process.stdout.readline()
            if output:
                print(output.strip())
                match = re.search(r'https://.*\.trycloudflare\.com', output)
                if match:
                    tunnel_url = match.group(0)
                    print(f"Tunnel URL: {tunnel_url}")
                    break
            elif tunnel_process.poll() is not None:
                break

        if not tunnel_url:
            raise Exception("Failed to obtain Cloudflare tunnel URL")

        # Set environment variable
        os.environ['CLOUDFLARE_TUNNEL_URL'] = tunnel_url

        # Start the Flask application
        print("Starting Flask application...")
        flask_process = subprocess.Popen(['python', 'test_app.py'])

        # Wait for both processes
        flask_process.wait()

    except KeyboardInterrupt:
        print("\nInterrupted by user. Shutting down...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cleanup(tunnel_process, flask_process)

if __name__ == "__main__":
    main()