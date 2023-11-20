import fsconfig
import logging

#### INODE LAYER


# This class holds an inode object in memory and provides methods to modify inodes
# The pattern here is:
#  0. Initialize the object
#  1. Read an Inode object from a byte array read from raw block storage (InodeFromBytearray)
#     An inode is stored in a raw block as a byte array:
#       size (bytes 0..3), type (bytes 4..5), refcnt (bytes 6..7), block_numbers (bytes 8..)
#  2. Update inode (e.g. size, refcnt, block numbers) depending on file system operation
#     Using various Set() methods
#  3. Serialize and write Inode object back to raw block storage (InodeToBytearray)

class Inode():
    def __init__(self):

        # an inode is initialized empty: invalid, zero size, no block numbers
        self.type = fsconfig.INODE_TYPE_INVALID
        self.size = 0
        self.refcnt = 0
        # We store inode block_numbers as a list
        self.block_numbers = []

        # initialize list with zeroes
        for i in range(0,fsconfig.MAX_INODE_BLOCK_NUMBERS):
            self.block_numbers.append(0)


    ## Set this inode's object (type, size, refcnt, block_numbers[]) from a raw bytearray b
    ## This is used when to pick an inode the inode table in raw block storage and create an inode object

    def InodeFromBytearray(self,b):

        if len(b) > fsconfig.INODE_SIZE:
            logging.error ('InodeFromBytearray: exceeds inode size ' + str(b))
            quit()

        # slice the raw bytes for the different fields
        # size is 4 bytes, type 2 bytes, refcnt 2 bytes
        # these add up to INODE_BYTES_SIZE_TYPE_REFCNT=8
        size_slice = b[0:4]
        type_slice = b[4:6]
        refcnt_slice = b[6:8]

        # converts from raw bytes to integers using big-endian
        # store scalars
        self.size = int.from_bytes(size_slice, byteorder='big')
        self.type = int.from_bytes(type_slice, byteorder='big')
        self.refcnt = int.from_bytes(refcnt_slice, byteorder='big')

        # each block number entry is INODE_BYTES_STORE_BLOCK_NUMBER bytes, big-endian
        # scan through the max number of blocks an inode can hold
        for i in range(0,fsconfig.MAX_INODE_BLOCK_NUMBERS):
            # the starting point is offset by INODE_BYTES_SIZE_TYPE_REFCNT=8
            start = 8 + i*4
            # pull a slice of only INODE_BYTES_STORE_BLOCK_NUMBER=4 bytes
            blocknumber_slice = b[start:start+4]
            # convert byte slice to an integer using big-endian
            self.block_numbers[i] = int.from_bytes(blocknumber_slice, byteorder='big')


    ## Create and return a raw byte array, serializing Inode object values to prepare to write
    ## This is used when we write an inode to raw block storage

    def InodeToBytearray(self):

        # Temporary bytearray - we'll load it with the different inode fields
        temparray = bytearray(fsconfig.INODE_SIZE)

        # We assume size is 4 bytes, and we store it in Big Endian format
        intsize = self.size
        temparray[0:4] = intsize.to_bytes(4, 'big')

        # We assume type is 2 bytes, and we store it in Big Endian format
        inttype = self.type
        temparray[4:6] = inttype.to_bytes(2, 'big')

        # We assume refcnt is 2 bytes, and we store it in Big Endian format
        intrefcnt = self.refcnt
        temparray[6:8] = intrefcnt.to_bytes(2, 'big')

        # We assume each block number is INODE_BYTES_STORE_BLOCK_NUMBER=4 bytes, and we store each in Big Endian format
        for i in range(0,fsconfig.MAX_INODE_BLOCK_NUMBERS):
            start = 8 + i*4
            intbn = self.block_numbers[i]
            temparray[start:start+4] = intbn.to_bytes(4, 'big')

        # Return the byte array
        return temparray


    ## Prints out this inode object's information to the log

    def Print(self):
        logging.info ('Inode size   : ' + str(self.size))
        logging.info ('Inode type   : ' + str(self.type))
        logging.info ('Inode refcnt : ' + str(self.refcnt))
        logging.info ('Block numbers: ')
        s = ""
        for i in range(0,fsconfig.MAX_INODE_BLOCK_NUMBERS):
            s += str(self.block_numbers[i])
            s += ","
        logging.info (s)
