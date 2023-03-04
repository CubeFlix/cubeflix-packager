# main.py
# Cubeflix packager.

import packager
import logging

logging.basicConfig(level=logging.INFO)

def main():
    import argparse

    parser = argparse.ArgumentParser(prog='cubeflix-packager', description="The Cubeflix internal packager utility.")
    parser.add_argument('-p', type=str, help='the path of the project JSON file', default='project.json')
    parser.add_argument('-o', type=str, help='the output path for releases', default='release')

    args = parser.parse_args()
    
    project = packager.load_project(args.p)
    project.release(args.o)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'cubeflix-packager: {e}')