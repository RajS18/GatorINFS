import fsconfig
import logging
from block import *
from inode import *

#### Inode number layer


class InodeNumber():
    def __init__(self, number):
        
        # The inode object stores the inode data structure
        self.inode = Inode()

        # This stores the inode number
        if number > fsconfig.MAX_NUM_INODES:
            logging.error ('InodeNumber::Init: inode number exceeds limit: ' + str(number))
            quit()
        self.inode_number = number


    ## Load an inode data structure from raw storage, indexed by inode number
    ## The inode data structure loaded from raw storage goes in the self.inode object
    ## Since one inode is a slice of a block in the inode table, we first Get() the inode table block, then extract the slice

    def InodeNumberToInode(self, RawBlocks):

        logging.debug('InodeNumber::InodeNumberToInode: ' + str(self.inode_number))

        # locate which block (in the inode table) has the inode we want
        inode_table_raw_block_number = fsconfig.INODE_BLOCK_OFFSET + ((self.inode_number * fsconfig.INODE_SIZE) // fsconfig.BLOCK_SIZE)

        # Read (Get) the entire block that contains inode from raw storage
        inode_table_raw_block = RawBlocks.Get(inode_table_raw_block_number)

        # Find the byte slice start:end within the block to select this particular inode_number
        start = (self.inode_number * fsconfig.INODE_SIZE) % fsconfig.BLOCK_SIZE
        end = start + fsconfig.INODE_SIZE

        # extract byte array for this inode
        inode_slice = inode_table_raw_block[start:end]

        # load inode from byte array
        self.inode.InodeFromBytearray(inode_slice)

        logging.debug ('InodeNumber::InodeNumberToInode: inode_number ' + str(self.inode_number) + ' raw_block_number: ' + str(inode_table_raw_block_number) + ' slice start: ' + str(start) + ' end: ' + str(end))
        logging.debug ('inode_slice: ' + str(inode_slice.hex()))


    ## Stores (Put) this inode into raw storage
    ## Since an inode is a slice of a block, we first Get() the block, update the slice, and Put()

    def StoreInode(self, RawBlocks):

        logging.debug('InodeNumber::StoreInode: ' + str(self.inode_number))

        # locate which block has the inode we want
        inode_table_raw_block_number = fsconfig.INODE_BLOCK_OFFSET + ((self.inode_number * fsconfig.INODE_SIZE) // fsconfig.BLOCK_SIZE)
        logging.debug('InodeNumber::StoreInode: inode_table_raw_block_number ' + str(inode_table_raw_block_number))

        # Get the entire block containing inode from raw storage
        inode_table_raw_block = RawBlocks.Get(inode_table_raw_block_number)
        logging.debug('InodeNumber::StoreInode: inode_table_raw_block:\n' + str(inode_table_raw_block.hex()))

        # Find the start:end byte slice of the block retrieved from the inode table for this particular inode_number
        start = (self.inode_number * fsconfig.INODE_SIZE) % fsconfig.BLOCK_SIZE
        end = start + fsconfig.INODE_SIZE
        logging.debug('InodeNumber::StoreInode: start: ' + str(start) + ', end: ' + str(end))

        # serialize inode into byte array
        inode_bytearray = self.inode.InodeToBytearray()

        # Update slice of block with this inode's serialized bytearray
        inode_table_raw_block[start:end] = inode_bytearray
        logging.debug('InodeNumber::StoreInode: tempblock:\n' + str(inode_table_raw_block.hex()))

        # Update raw storage with new inode
        RawBlocks.Put(inode_table_raw_block_number, inode_table_raw_block)


    ## Returns a block of data from raw storage, given its file offset
    ## Equivalent to textbook's INODE_NUMBER_TO_BLOCK on page 96

    def InodeNumberToBlock(self, RawBlocks, offset):

        logging.debug ('InodeNumber::InodeNumberToBlock: ' + str(offset))

        # Load object's inode
        self.InodeNumberToInode(RawBlocks)

        # Calculate offset
        o = offset // fsconfig.BLOCK_SIZE

        # Retrieve block indexed by offset
        # as in the textbook's INDEX_TO_BLOCK_NUMBER - here self.inode is equivalent to the book's i
        b = self.inode.block_numbers[o]

        # Read the block from raw storage - here Get() is equivalent to BLOCK_NUMBER_TO_BLOCK
        block = RawBlocks.Get(b)

        # return the block
        return block
