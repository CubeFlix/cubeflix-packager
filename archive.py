# archive.py
# Cubeflix Binary Format Archives

import cbf, os

# Compress a CBF archive.
def compress(path, output):
    # Load the dataset.
    dataset = _load_path(path)
    
    # Write the file.
    with open(output, 'wb') as f:
        cbf.dump(dataset, f)

# Recursively load a path into a dataset.
def _load_path(path):
    dataset = {}
    
    # Iterate over the path.
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path):
            # File.
            dataset[item] = cbf.FileWritableBlob(item_path)
        else:
            # Folder.
            dataset[item] = _load_path(item_path)

    return dataset

# Extract a CBF archive.
def extract(path, output, chunk_size=65536):
    # Load the file.
    with open(path, 'rb') as f:
        dataset = cbf.load(f)

        # Extract the path.
        _extract_path(dataset, output, chunk_size)
        
# Recursively extract a path dataset.
def _extract_path(dataset, path, chunk_size):
    # Create the directory.
    os.mkdir(path)

    # Iterate over each item.
    for key, val in dataset.items():
        if isinstance(val, cbf.ReadableBlob):
            # File.
            with open(os.path.join(path, key), 'wb') as f:
                i = 0
                while i < val.size:
                    amount_to_write = chunk_size if i + chunk_size <= val.size else (val.size - i)
                    f.write(val.read(amount_to_write, i))
                    i += amount_to_write
        elif isinstance(val, dict):
            # Folder.
            _extract_path(val, os.path.join(path, key), chunk_size)
        else:
            raise cbf.InvalidCBFFileError("invalid cbf archive")

def main():
    import argparse

    parser = argparse.ArgumentParser(prog='cbf-archive')
    subparser = parser.add_subparsers(dest='command')
    compress_parser = subparser.add_parser('compress')
    extract_parser = subparser.add_parser('extract')

    compress_parser.add_argument('path', type=str, help='the path to compress')
    compress_parser.add_argument('-o', type=str, help='the output path', required=False)
    extract_parser.add_argument('path', type=str, help='the path of the archive')
    extract_parser.add_argument('-o', type=str, help='the output path to extract to', required=False)

    args = parser.parse_args()

    if args.command == 'compress':
        if not args.o:
            args.o = os.path.basename(args.path) + '.cbf'
        compress(args.path, args.o)
    elif args.command == 'extract':
        if not args.o:
            args.o = os.path.splitext(os.path.basename(args.path))[0]
        extract(args.path, args.o)
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'cbf-archive: {e}')