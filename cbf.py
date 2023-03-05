# cbf.py
# Cubeflix Binary Format

"""The Cubeflix Binary Format (CBF)."""

import io, struct, os, shutil

class WritableBlob:

    """A writable blob object."""

    @property
    def length(self):
        raise NotImplementedError()

    def dump(self, file):
        raise NotImplementedError()

class FileWritableBlob(WritableBlob):

    """A writable blob that loads in a file."""

    length = NotImplemented

    def __init__(self, path):
        
        """Create the file writable blob."""

        self.path = path
        self.length = os.path.getsize(path)

    def dump(self, file):

        """Write the file to the given file."""

        with open(self.path, 'rb') as ourfile:
            shutil.copyfileobj(ourfile, file)

class ReadableBlob:

    """A readable blob object."""

    def __init__(self, file, location, size):

        """Create the readable blob object."""

        self.file = file
        self.location = location
        self.size = size
    
    def read(self, n, offset=0):

        """Read n bytes starting at offset."""

        if offset + n > self.size:
            raise EOFError("end of blob")

        self.file.seek(self.location + offset)
        return self.file.read(n)

    def read_all(self):

        """Read the entire blob."""

        self.file.seek(self.location)
        return self.file.read(self.size)

class SizeError(Exception):
    pass

class InvalidCBFFileError(Exception):
    pass

CBF_VERSION = 'A'
CBF_HEADER = 'CB' + CBF_VERSION

# Data type values.
TYPE_NONE = 0x00
TYPE_BLOB = 0x01
TYPE_DATASET = 0x02
TYPE_STRING = 0x03
TYPE_INT = 0x04
TYPE_UINT = 0x05
TYPE_FLOAT = 0x06
TYPE_BYTES = 0x07
TYPE_BOOL = 0x08

VALID_TYPES = (type(None), WritableBlob, dict, str, int, float, bytes, bool)

MAX_KEY_LEN = 65535

# Dump a CBF dataset to a file.
def dump(dataset, file):

    """Dump a CBF dataset to a file."""

    if not isinstance(dataset, dict):
        raise TypeError(f"dump requires a dictionary object as dataset argument, not {type(dataset)}")

    if not isinstance(file, io.BufferedWriter):
        raise TypeError(f"dump requires a buffered writer as file argument, not {type(file)}")

    # Calculate the position of the binary section. Length of the header plus 
    # the length of the dataset.
    binary_starting_offset = 3 + _calculate_block_size(dataset)
    
    # Write the header.
    file.write(CBF_HEADER.encode('ascii'))

    # Write the dataset.
    _dump_block(dataset, file, binary_starting_offset)

    # Write the binary section.
    _dump_binary(dataset, file)

# Calculate the total size of a dataset block.
def _calculate_block_size(dataset):
    # Account for the length value.
    size = 8
    
    # Iterate over the dataset and sum up the size of the block.
    for key, value in dataset.items():
        # Account for the data type value.
        size += 1

        if not isinstance(key, str):
            raise TypeError(f"keys must be strings, not type {type(key)}")
        if len(key) > MAX_KEY_LEN:
            raise SizeError(f"key {key} is too long")

        # Account for the key value.
        size += 2 + len(key)

        if isinstance(value, type(None)):
            # None type.
            pass
        elif isinstance(value, WritableBlob):
            # Blob type.
            size += 16
        elif isinstance(value, dict):
            # Dataset type.
            size += _calculate_block_size(value)
        elif isinstance(value, str):
            # String type.
            size += 8 + len(value.encode('utf-8'))
        elif isinstance(value, int):
            # Int type.
            size += 8
        elif isinstance(value, float):
            # Float type.
            size += 8
        elif isinstance(value, (bytes, bytearray)):
            # Bytes type.
            size += 8 + len(value)
        elif isinstance(value, bool):
            # Bool type.
            size += 1
        else:
            raise TypeError(f"value has invalid type: {type(value)}")

    return size

# Dump a CBF dataset block to a file. The current_estimated_file_length 
# parameter is the current estimated file length, required for calculating 
# pointers to regions of data within the binary section. Returns the new
# current estimated file length.
def _dump_block(dataset, file, current_estimated_file_length):
    # Write the length of the dataset.
    file.write(len(dataset).to_bytes(8, 'little'))

    # Iterate over the dataset and write each key-value pair.
    for key, value in dataset.items():
        # Write the key.
        file.write(len(key).to_bytes(2, 'little'))
        file.write(key.encode('ascii'))

        # Write the data value.
        if isinstance(value, type(None)):
            # None type.
            file.write(bytes([TYPE_NONE]))
        elif isinstance(value, WritableBlob):
            # Blob type. We will place the blob data in the binary section, 
            # so we can predict that the location of the blob will be the
            # current estimated file length. We will then update the current
            # estimated file length for the next blob object.
            file.write(bytes([TYPE_BLOB]))
            file.write(current_estimated_file_length.to_bytes(8, 'little'))
            file.write(value.length.to_bytes(8, 'little'))
            current_estimated_file_length += value.length
        elif isinstance(value, dict):
            # Dataset type.
            file.write(bytes([TYPE_DATASET]))
            current_estimated_file_length = _dump_block(value, file, current_estimated_file_length)
        elif isinstance(value, str):
            # String type.
            file.write(bytes([TYPE_STRING]))
            file.write(len(value).to_bytes(8, 'little'))
            file.write(value.encode('utf-8'))
        elif isinstance(value, int):
            # Int type.
            file.write(bytes([TYPE_INT]))
            file.write(value.to_bytes(8, 'little'))
        elif isinstance(value, float):
            # Float type.
            file.write(bytes([TYPE_FLOAT]))
            file.write(struct.pack('d', value))
        elif isinstance(value, (bytes, bytearray)):
            # Bytes type.
            file.write(bytes([TYPE_BYTES]))
            file.write(len(value).to_bytes(8, 'little'))
            file.write(value)
        elif isinstance(value, bool):
            # Bool type.
            file.write(bytes([TYPE_BOOL]))
            if value:
                file.write(b'\xff')
            else:
                file.write(b'\x00')
        else:
            raise TypeError(f"value has invalid type: {type(value)}")

    return current_estimated_file_length

# Dump the CBF binary section to a file. Takes a dataset and adds each blob 
# in order.
def _dump_binary(dataset, file):
    # Iterate over the dataset and write all the blobs.
    for value in dataset.values():
        if isinstance(value, WritableBlob):
            # Blob type. Write the blob.
            value.dump(file)
        elif isinstance(value, dict):
            # Dataset type. Recursively dump the datasets contents.
            _dump_binary(value, file)

# Load a CBF file.
def load(file):
    if not isinstance(file, io.BufferedReader):
        raise TypeError(f"load requires a buffered reader as file argument, not {type(file)}")

    # Read the header.
    header = file.read(3)
    if header != CBF_HEADER.encode('ascii'):
        raise InvalidCBFFileError('invalid header')

    # Read the dataset section.
    return _load_block(file)

# Load a dataset block from a file.
def _load_block(file):
    # Get the length of the dataset block.
    length = int.from_bytes(file.read(8), 'little', signed=False)
    
    block = {}

    # Read each key-value pair and reconstruct the block.
    for _ in range(length):
        # Read the key.
        key_len = int.from_bytes(file.read(2), 'little', signed=False)
        key = file.read(key_len).decode('ascii')
        value = None

        # Read the data type.
        data_type = file.read(1)[0]
        if data_type == TYPE_NONE:
            value = None
        elif data_type == TYPE_BLOB:
            location = int.from_bytes(file.read(8), 'little', signed=False)
            size = int.from_bytes(file.read(8), 'little', signed=False)
            value = ReadableBlob(file, location, size)
        elif data_type == TYPE_DATASET:
            value = _load_block(file)
        elif data_type == TYPE_STRING:
            str_len = int.from_bytes(file.read(8), 'little', signed=False)
            value = file.read(str_len).decode('utf-8')
        elif data_type == TYPE_INT:
            value = int.from_bytes(file.read(8), 'little', signed=True)
        elif data_type == TYPE_UINT:
            value = int.from_bytes(file.read(8), 'little', signed=False)
        elif data_type == TYPE_FLOAT:
            value = struct.unpack('d', file.read(8))
        elif data_type == TYPE_BYTES:
            bytes_len = int.from_bytes(file.read(8), 'little', signed=False)
            value = file.read(bytes_len)
        elif data_type == TYPE_BOOL:
            raw_val = file.read(1)[0]
            if raw_val == 0x00:
                value = False
            elif raw_val == 0xff:
                value = True
            else:
                raise InvalidCBFFileError('invalid boolean value')
        else:
            raise InvalidCBFFileError('invalid data type')

        block[key] = value
    
    return block