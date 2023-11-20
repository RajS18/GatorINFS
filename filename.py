import fsconfig
import logging
from block import *
from inode import *
from inodenumber import *

#### File name layer


## This class implements methods for the file name layer

class FileName():
    def __init__(self, RawBlocks):
        ## Initialize a reference to the rawblocks object
        self.RawBlocks = RawBlocks

    ## This helper function extracts a file name string from a directory data block
    ## The index selects which file name entry to extract within the block - e.g. index 0 is the first file name, 1 second file name

    def HelperGetFilenameString(self, block, index):
        logging.debug('FileName::HelperGetFilenameString: ' + str(block.hex()) + ', ' + str(index))

        # Locate bytes that store string - first MAX_FILENAME characters aligned by MAX_FILENAME + INODE_NUMBER_DIRENTRY_SIZE
        string_start = index * fsconfig.FILE_NAME_DIRENTRY_SIZE
        string_end = string_start + fsconfig.MAX_FILENAME
        return block[string_start:string_end]


    ## This helper function extracts an inode number from a directory data block
    ## The index selects which entry to extract within the block - e.g. index 0 is the inode for the first file name, 1 second file name

    def HelperGetFilenameInodeNumber(self, block, index):
        logging.debug('FileName::HelperGetFilenameInodeNumber: ' + str(block.hex()) + ', ' + str(index))

        # Locate bytes that store inode
        inode_start = (index * fsconfig.FILE_NAME_DIRENTRY_SIZE) + fsconfig.MAX_FILENAME
        inode_end = inode_start + fsconfig.INODE_NUMBER_DIRENTRY_SIZE
        inodenumber_slice = block[inode_start:inode_end]
        # convert from a byte slice to an integer; we use big-endian encoding
        return int.from_bytes(inodenumber_slice, byteorder='big')


    ## Scans inode table to find an INVALID entry that can be used to hold a new inode

    def FindAvailableInode(self):

        logging.debug('FileName::FindAvailableInode: ')

        for i in range(0, fsconfig.MAX_NUM_INODES):
            # Initialize inode_number object from raw storage
            inode_number = InodeNumber(i)
            inode_number.InodeNumberToInode(self.RawBlocks)
            # the integer inode number of first INVALID inode found is returned
            if inode_number.inode.type == fsconfig.INODE_TYPE_INVALID:
                logging.debug("FileName::FindAvailableInode: " + str(i))
                return i

        logging.debug("FileName::FindAvailableInode: no available inodes")
        return -1

    ## Returns index to an available entry in directory, if there is room for new entry

    def FindAvailableFileEntry(self, dir):

        logging.debug('FileName::FindAvailableFileEntry: dir: ' + str(dir))

        # Initialize inode_number object from raw storage
        inode_number = InodeNumber(dir)
        inode_number.InodeNumberToInode(self.RawBlocks)

        # Check if there is still room for another (filename,inode) entry
        # the inode cannot exceed maximum size
        if inode_number.inode.size >= fsconfig.MAX_FILE_SIZE:
            logging.debug("FileName::FindAvailableFileEntry: no entries available")
            return -1

        logging.debug("FileName::FindAvailableFileEntry: " + str(inode_number.inode.size))
        return inode_number.inode.size


    ## Allocate a data block, update free bitmap, and return its number

    def AllocateDataBlock(self):

        logging.debug('FileName::AllocateDataBlock: ')

        # Scan through all available data blocks in the free bitmap to see if there's any free ones
        for block_number in range(fsconfig.DATA_BLOCKS_OFFSET, fsconfig.TOTAL_NUM_BLOCKS):

            # GET() raw block that stores the bitmap entry for block_number
            bitmap_block = fsconfig.FREEBITMAP_BLOCK_OFFSET + (block_number // fsconfig.BLOCK_SIZE)
            block = self.RawBlocks.Get(bitmap_block)

            # Locate the proper byte the refers to block_number within the free bitmap block
            byte_bitmap = block[block_number % fsconfig.BLOCK_SIZE]

            # Data block block_number is free
            if byte_bitmap == 0:
                # Mark it as used in bitmap
                block[block_number % fsconfig.BLOCK_SIZE] = 1
                # Write it back to the free bitmap in raw storage
                self.RawBlocks.Put(bitmap_block, block)
                logging.debug('FileName::AllocateDataBlock: allocated ' + str(block_number))
                return block_number

        logging.debug('FileName::AllocateDataBlock: no free data blocks available')
        quit()

    ## This inserts a (filename,inodenumber) entry into the tail end of the table in a directory data block of insert_to
    ## insert_to is an InodeNumber() object - the inode number of the directory where this entry is to be inserted
    ## filename is a string
    ## inodenumber is an integer
    ## Used when adding an entry to a directory
    ## insert_into is an InodeNumber() object; filename is a string; inodenumber is an integer

    def InsertFilenameInodeNumber(self, insert_to, filename, inodenumber):
        logging.debug('FileName::InsertFilenameInodeNumber: ' + str(filename) + ', ' + str(inodenumber))

        # bound and type checks first
        if len(filename) > fsconfig.MAX_FILENAME:
            logging.error('FileName::InsertFilenameInodeNumber: file name exceeds maximum')
            quit()

        if insert_to.inode.type != fsconfig.INODE_TYPE_DIR:
            logging.error('FileName::InsertFilenameInodeNumber: not a directory inode: ' + str(insert_to.inode.type))
            quit()

        # We need to insert this new entry at the end of the existing directory table
        # So we first need to determine this position based on the directory inode's size
        index = insert_to.inode.size
        # If there's no space for another entry in the directory, we abort
        # Note that a directory or file can be at most fsconfig.MAX_FILE_SIZE bytes
        if index >= fsconfig.MAX_FILE_SIZE:
            logging.error('FileName::InsertFilenameInodeNumber: no space for another entry in inode')
            quit()

        # Check if we need to allocate another data block for this inode
        # this happens when the index spills over to the next block
        # first, find the block number index for the directory's inode
        block_number_index = index // fsconfig.BLOCK_SIZE
        if index % fsconfig.BLOCK_SIZE == 0:
            # index == 0 is a special case as an inode is initialized with one data block; so no need to allocate
            if index != 0:
                # Allocate the data block to store this binding
                new_block = self.AllocateDataBlock()
                # update directory inode to add this new block to the list of block_numbers
                # note: inode will be written to raw storage before the method returns
                insert_to.inode.block_numbers[block_number_index] = new_block

        # Retrieve the full data block where the new (filename,inodenumber) will be stored
        block_number = insert_to.inode.block_numbers[block_number_index]
        block = self.RawBlocks.Get(block_number)

        # Compute modulo of index to locate within this data block where the new entry should be added
        index_modulo = index % fsconfig.BLOCK_SIZE

        # the entry to insert has two components: the file name string, and the inode number
        # we need byte slices for both
        # Now compute the byte slice holding the stirng file name with MAX_FILENAME size
        string_start = index_modulo
        string_end = string_start + fsconfig.MAX_FILENAME
        # convert file name to bytearray to insert the slice in block
        stringbyte = bytearray(filename, "utf-8")

        # Now compute the byte slice holding the inode number with INODE_NUMBER_DIRENTRY_SIZE size
        inode_start = index_modulo + fsconfig.MAX_FILENAME
        inode_end = inode_start + fsconfig.INODE_NUMBER_DIRENTRY_SIZE

        logging.debug('FileName::InsertFilenameInodeNumber: block read \n' + str(block.hex()))
        logging.debug('FileName::InsertFilenameInodeNumber: string_start ' + str(string_start) + ', string_end ' + str(string_end))
        logging.debug('FileName::InsertFilenameInodeNumber: inode_start ' + str(inode_start) + ', inode_end ' + str(inode_end))

        # Update and write data block with (filename,inode) mapping
        # pad the bytearray representation of the string with zeroes if the filename is smaller than MAX_FILENAME
        block[string_start:string_end] = bytearray(stringbyte.ljust(fsconfig.MAX_FILENAME, b'\x00'))
        block[inode_start:inode_end] = inodenumber.to_bytes(fsconfig.INODE_NUMBER_DIRENTRY_SIZE, 'big')
        # Write the updated block to raw block storage
        self.RawBlocks.Put(block_number, block)

        # Now update the inode of the directory - need to increment its size
        # Increment size to reflect that a new entry has been appended
        logging.debug('FileName::InsertFilenameInodeNumber: insert_to.inode.size ' + str(insert_to.inode.size))
        insert_to.inode.size += fsconfig.FILE_NAME_DIRENTRY_SIZE
        # Write updated inode back to inode table in raw block storage
        insert_to.StoreInode(self.RawBlocks)


    ## Initializes the root inode and store in inode table in raw storage:
    ## type DIR, size 0, refcnt 1

    def InitRootInode(self):

        logging.debug('FileName::InitRootInode')

        # Root inode has well-known value 0; create an InodeNumber object
        root_inode = InodeNumber(0)
        root_inode.InodeNumberToInode(self.RawBlocks)
        root_inode.inode.type = fsconfig.INODE_TYPE_DIR
        root_inode.inode.size = 0
        root_inode.inode.refcnt = 1
        # Allocate one data block and set as first entry in block_numbers[]
        logging.debug('FileName::InitRootInode: calling AllocateDataBlock')
        root_inode.inode.block_numbers[0] = self.AllocateDataBlock()
        # Add a binding from "." to 0 in this newly created data block
        logging.debug('FileName::InitRootInode: calling InsertFilenameInodeNumber')
        self.InsertFilenameInodeNumber(root_inode, ".", 0)
        ## print for debugging
        # root_inode.inode.Print()
        logging.debug('FileName::InitRootInode: calling StoreInode')
        root_inode.StoreInode(self.RawBlocks)


    ## Lookup string filename in the context of inode dir
    ## This follows the same logic as the textbook's LOOKUP in p98

    def Lookup(self, filename, dir):
        logging.debug('FileName::Lookup: ' + str(filename) + ', ' + str(dir))

        # Initialize inode_number object for directory from raw storage
        inode_number = InodeNumber(dir)
        inode_number.InodeNumberToInode(self.RawBlocks)

        if inode_number.inode.type != fsconfig.INODE_TYPE_DIR:
            logging.error("FileName::Lookup: not a directory inode: " + str(dir) + " , " + str(inode_number.inode.type))
            return -1

        # Iterate over all data blocks indexed by directory inode, until we reach inode's size
        offset = 0
        scanned = 0
        while offset < inode_number.inode.size:

            # Retrieve directory data block given current offset
            b = inode_number.InodeNumberToBlock(self.RawBlocks, offset)

            # A directory data block has multiple (filename,inode) entries
            # Iterate over file entries to search for matches
            for i in range(0, fsconfig.FILE_ENTRIES_PER_DATA_BLOCK):
                # don't search beyond bounds (the size of the directory)
                if inode_number.inode.size > scanned:
                    scanned += fsconfig.FILE_NAME_DIRENTRY_SIZE

                    # Extract padded MAX_FILENAME string as a bytearray from data block for comparison
                    filestring = self.HelperGetFilenameString(b, i)
                    logging.debug("FileName::Lookup for " + filename + " in " + str(dir) + ": searching string " + str(filestring))
                    # Pad filename with zeroes and make it a byte array
                    padded_filename = bytearray(filename, "utf-8")
                    padded_filename = bytearray(padded_filename.ljust(fsconfig.MAX_FILENAME, b'\x00'))

                    # these are now two byte arrays of the same MAX_FILENAME size, ready for simple == comparison
                    if filestring == padded_filename:
                        # On a match, lookup is successful - retrieve the inode number and return it
                        fileinode = self.HelperGetFilenameInodeNumber(b, i)
                        logging.debug("FileName::Lookup successful: " + str(fileinode))
                        return fileinode

            # Skip to the search on next block, and back to while loop
            offset += fsconfig.BLOCK_SIZE

        logging.debug("FileName::Lookup: file not found: " + str(filename) + " in " + str(dir))
        return -1

