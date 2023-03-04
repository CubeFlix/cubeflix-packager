# main.py
# Cubeflix packager.

import packager

def main():
    import argparse

    parser = argparse.ArgumentParser(prog='cubeflix-packager', description="The Cubeflix internal packager utility.")
    parser.add_argument('path', type=str, help='the path of the project JSON file', default='project.json')
    parser.add_argument('output', type=str, help='the output path for releases', default='release')

    args = parser.parse_args()
    
    project = packager.load_project(args.path)
    project.release(args.output)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'cubeflix-packager: {e}')