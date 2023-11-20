import logging, argparse

##### File system constants
global TOTAL_NUM_BLOCKS, BLOCK_SIZE, MAX_NUM_INODES, INODE_SIZE
global INODE_TYPE_INVALID, INODE_TYPE_FILE, INODE_TYPE_DIR, INODE_TYPE_SYM
global INODES_PER_BLOCK, FREEBITMAP_NUM_BLOCKS, INODE_BLOCK_OFFSET, INODE_NUM_BLOCKS, MAX_INODE_BLOCK_NUMBERS, \
        MAX_FILE_SIZE, DATA_BLOCKS_OFFSET, DATA_NUM_BLOCKS, FILE_NAME_DIRENTRY_SIZE, FILE_ENTRIES_PER_DATA_BLOCK
global CID, PORT, MAX_CLIENTS, SERVER_ADDRESS, RSM_UNLOCKED, RSM_LOCKED, SOCKET_TIMEOUT, RETRY_INTERVAL

# Useful variables that are derived from the above
# Call this function to compute derived file system parameters

def ConfigureFSConstants(args):
    # Basic and derived file system configuration parameters are stored in global variables
    # Call this function with args (from command-line arguments) to configure the file system

    global TOTAL_NUM_BLOCKS, BLOCK_SIZE, MAX_NUM_INODES, INODE_SIZE
    global CID, PORT, MAX_CLIENTS, SERVER_ADDRESS, RSM_UNLOCKED, RSM_LOCKED, SOCKET_TIMEOUT, RETRY_INTERVAL
    # Default values
    # Total number of blocks in raw storage
    TOTAL_NUM_BLOCKS = 256
    # Block size (in Bytes)
    BLOCK_SIZE = 128
    # Maximum number of inodes
    MAX_NUM_INODES = 16
    # Size of an inode (in Bytes)
    INODE_SIZE = 16
    CID = 0
    PORT = 8000

    # Override defaults if provided in command line arguments (args)
    if args.total_num_blocks:
        TOTAL_NUM_BLOCKS = args.total_num_blocks
    if args.block_size:
        BLOCK_SIZE = args.block_size
    if args.max_num_inodes:
        MAX_NUM_INODES = args.max_num_inodes
    if args.inode_size:
        INODE_SIZE = args.inode_size
    if args.client_id:
        CID = args.client_id
    if args.port:
        PORT = args.port

    # These are constants that SHOULD NEVER BE MODIFIED
    global MAX_FILENAME, INODE_NUMBER_DIRENTRY_SIZE, FREEBITMAP_BLOCK_OFFSET, INODE_BYTES_SIZE_TYPE_REFCNT, \
            INODE_BYTES_STORE_BLOCK_NUMBER

    # Maximum file name (in characters)
    MAX_FILENAME = 12
    # Number of Bytes to store an inode number in directory entry
    INODE_NUMBER_DIRENTRY_SIZE = 4
    # To be consistent with book, block 0 is root block, 1 superblock
    # Bitmap of free blocks starts at offset 2
    FREEBITMAP_BLOCK_OFFSET = 2
    # Number of bytes used to store size, type, refcnt in an inode
    #   4 bytes for size
    #   2 bytes for type
    #   2 bytes for refcnt
    INODE_BYTES_SIZE_TYPE_REFCNT = 8
    # Number of bytes used in an inode to store a block number
    INODE_BYTES_STORE_BLOCK_NUMBER = 4

    # Supported inode types
    global INODE_TYPE_INVALID, INODE_TYPE_FILE, INODE_TYPE_DIR, INODE_TYPE_SYM
    INODE_TYPE_INVALID = 0
    INODE_TYPE_FILE = 1
    INODE_TYPE_DIR = 2
    INODE_TYPE_SYM = 3


    # Parameters derived from the above
    global INODES_PER_BLOCK, FREEBITMAP_NUM_BLOCKS, INODE_BLOCK_OFFSET, INODE_NUM_BLOCKS, MAX_INODE_BLOCK_NUMBERS, \
        MAX_FILE_SIZE, DATA_BLOCKS_OFFSET, DATA_NUM_BLOCKS, FILE_NAME_DIRENTRY_SIZE, FILE_ENTRIES_PER_DATA_BLOCK

    # Number of inodes that fit in a block
    INODES_PER_BLOCK = BLOCK_SIZE // INODE_SIZE

    # Number of blocks needed for free bitmap
    # For simplicity, we assume each entry in the bitmap is a Byte in length
    # This allows us to avoid bit-wise operations
    FREEBITMAP_NUM_BLOCKS = TOTAL_NUM_BLOCKS // BLOCK_SIZE

    # inode table starts at offset 2 + FREEBITMAP_NUM_BLOCKS
    INODE_BLOCK_OFFSET = 2 + FREEBITMAP_NUM_BLOCKS

    # inode table size
    INODE_NUM_BLOCKS = (MAX_NUM_INODES * INODE_SIZE) // BLOCK_SIZE

    # maximum number of blocks indexed by inode
    # In total, 4+2+2=8 bytes are used for size+type+refcnt, remaining bytes for block numbers
    MAX_INODE_BLOCK_NUMBERS = (INODE_SIZE - INODE_BYTES_SIZE_TYPE_REFCNT) // INODE_BYTES_STORE_BLOCK_NUMBER

    # maximum size of a file
    # maximum number of entries in an inode's block_numbers[], times block size
    MAX_FILE_SIZE = MAX_INODE_BLOCK_NUMBERS*BLOCK_SIZE

    # Data blocks start at INODE_BLOCK_OFFSET + INODE_NUM_BLOCKS
    DATA_BLOCKS_OFFSET = INODE_BLOCK_OFFSET + INODE_NUM_BLOCKS

    # Number of data blocks
    DATA_NUM_BLOCKS = TOTAL_NUM_BLOCKS - DATA_BLOCKS_OFFSET

    # Size of a directory entry: file name plus inode size
    FILE_NAME_DIRENTRY_SIZE = MAX_FILENAME + INODE_NUMBER_DIRENTRY_SIZE

    # Number of filename+inode entries that can be stored in a single block
    FILE_ENTRIES_PER_DATA_BLOCK = BLOCK_SIZE // FILE_NAME_DIRENTRY_SIZE

    # For locks: RSM_UNLOCKED=0 , RSM_LOCKED=1
    RSM_UNLOCKED = bytearray(b'\x00') * 1
    RSM_LOCKED = bytearray(b'\x01') * 1


    # server address - default is 127.0.0.1, localhost
    SERVER_ADDRESS = '127.0.0.1'
    MAX_CLIENTS = 8
    SOCKET_TIMEOUT = 5
    RETRY_INTERVAL = 10


## Prints out file system information

def PrintFSConstants():
    print ('#### File system information:')
    print ('Number of blocks          : ' + str(TOTAL_NUM_BLOCKS))
    print ('Block size (Bytes)        : ' + str(BLOCK_SIZE))
    print ('Number of inodes          : ' + str(MAX_NUM_INODES))
    print ('inode size (Bytes)        : ' + str(INODE_SIZE))
    print ('inodes per block          : ' + str(INODES_PER_BLOCK))
    print ('Free bitmap offset        : ' + str(FREEBITMAP_BLOCK_OFFSET))
    print ('Free bitmap size (blocks) : ' + str(FREEBITMAP_NUM_BLOCKS))
    print ('Inode table offset        : ' + str(INODE_BLOCK_OFFSET))
    print ('Inode table size (blocks) : ' + str(INODE_NUM_BLOCKS))
    print ('Max blocks per file       : ' + str(MAX_INODE_BLOCK_NUMBERS))
    print ('Data blocks offset        : ' + str(DATA_BLOCKS_OFFSET))
    print ('Data block size (blocks)  : ' + str(DATA_NUM_BLOCKS))
    print ('Raw block layer layout: (B: boot, S: superblock, F: free bitmap, I: inode, D: data')
    Layout = "BS"
    Id = "01"
    IdCount = 2
    for i in range(0,FREEBITMAP_NUM_BLOCKS):
      Layout += "F"
      Id += str(IdCount)
      IdCount = (IdCount + 1) % 10
    for i in range(0,INODE_NUM_BLOCKS):
      Layout += "I"
      Id += str(IdCount)
      IdCount = (IdCount + 1) % 10
    for i in range(0,DATA_NUM_BLOCKS):
      Layout += "D"
      Id += str(IdCount)
      IdCount = (IdCount + 1) % 10
    print (Id)
    print (Layout)

