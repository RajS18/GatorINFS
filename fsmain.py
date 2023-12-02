import pickle, logging
import argparse
import fsconfig

from block import *
from shell import *
from filename import *
from fileoperations import *
from absolutepath import *

import os.path

if __name__ == "__main__":

    # Initialize file for logging
    # Change logging level to INFO to remove debugging messages
    logging.basicConfig(filename='memoryfs.log', filemode='w', level=logging.DEBUG)

    # Redirect INFO logs to console as well
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(console_handler)

    # Construct the argument parser
    ap = argparse.ArgumentParser()
    ap.add_argument('-nb', '--total_num_blocks', type=int, help='an integer value')
    ap.add_argument('-bs', '--block_size', type=int, help='an integer value')
    ap.add_argument('-ni', '--max_num_inodes', type=int, help='an integer value')
    ap.add_argument('-is', '--inode_size', type=int, help='an integer value')
    ap.add_argument('-cid', '--client_id', type=int, help='an integer value')
    ap.add_argument('-port', '--port', type=int, help='an integer value')
    ap.add_argument('-ns', '--number_of_servers',type=int, help='an integer number')
    ap.add_argument('-logcache','--logcache',type=int, help='must by 0 or 1')
    ap.add_argument('-startport','--startport',type=int, help='must be a valid available port number')

    # Other than FS args, consecutive args will be captured in by 'arg' as list
    ap.add_argument('arg', nargs='*')

    # Parse arguments
    args = ap.parse_args()

    # Initialize file system configuration
    fsconfig.ConfigureFSConstants(args)

    # Show file system information
    # fsconfig.PrintFSConstants()

    # Initialize empty file system data in raw storage
    RawBlocks = DiskBlocks()
    # RawBlocks.PrintBlocks("Initialized", 0, 16)

    # Create a FileName object and initialize the root's inode
    FileObject = FileName(RawBlocks)
    FileObject.InitRootInode()

    # Create a FileOperations object
    FileOperationsObject = FileOperations(FileObject)

    # Create a AbsolutePath object
    AbsolutePathObject = AbsolutePathName(FileObject)

    # Run the interactive shell interpreter
    myshell = FSShell(RawBlocks, FileOperationsObject, AbsolutePathObject)
    myshell.Interpreter()

