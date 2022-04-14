import argparse
from winerp.server import Server

def run():
    """ Module entry point"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-p",
        "--port",
        nargs='?',
        help="The port for winerp server",
        default=13254
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="print the version"
    )
    args = parser.parse_args()

    # Setup config from arguments
    port = args.port
    try:
        port = int(port)
    except:
        raise ValueError("port should be an integer between range 1-65535")
    
    if args.version:
        print('winerp version: unknown')
    else:
        print("Starting server at port: ", port)
        server = Server(port=port)
        server.start()


if __name__ == '__main__':
    run()
