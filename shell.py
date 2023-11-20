import fsconfig
import os.path

from block import *
from inode import *
from inodenumber import *
from filename import *
from fileoperations import *
from absolutepath import *

## This class implements an interactive shell to navigate the file system


class FSShell:
    def __init__(self, RawBlocks, FileOperationsObject, AbsolutePathObject):
        # cwd stored the inode of the current working directory
        # we start in the root directory
        self.cwd = 0
        self.FileOperationsObject = FileOperationsObject
        self.AbsolutePathObject = AbsolutePathObject
        self.RawBlocks = RawBlocks

    # block-layer inspection, load/save, and debugging shell commands
    # implements showfsconfig (log fs config contents)
    def showfsconfig(self):
        fsconfig.PrintFSConstants()
        return 0

    # implements showinode (log inode i contents)
    def showinode(self, i):
        try:
            i = int(i)
        except ValueError:
            print("Error: " + i + " not a valid Integer")
            return -1

        if i < 0 or i >= fsconfig.MAX_NUM_INODES:
            print(
                "Error: inode number "
                + str(i)
                + " not in valid range [0, "
                + str(fsconfig.MAX_NUM_INODES - 1)
                + "]"
            )
            return -1
        inobj = InodeNumber(i)
        inobj.InodeNumberToInode(self.RawBlocks)
        inode = inobj.inode
        inode.Print()
        return 0

    # implements load (load the specified dump file)
    def load(self, dumpfilename):
        if not os.path.isfile(dumpfilename):
            print("Error: Please provide valid file")
            return -1
        self.RawBlocks.LoadFromDump(dumpfilename)
        self.cwd = 0
        return 0

    # implements save (save the file system contents to specified dump file)
    def save(self, dumpfilename):
        self.RawBlocks.DumpToDisk(dumpfilename)
        return 0

    # implements showblock (log block n contents)
    def showblock(self, n):
        try:
            n = int(n)
        except ValueError:
            print("Error: " + n + " not a valid Integer")
            return -1
        if n < 0 or n >= fsconfig.TOTAL_NUM_BLOCKS:
            print(
                "Error: block number "
                + str(n)
                + " not in valid range [0, "
                + str(fsconfig.TOTAL_NUM_BLOCKS - 1)
                + "]"
            )
            return -1
        print(
            "Block (showing any string snippets in block the block) ["
            + str(n)
            + "] : \n"
            + str((self.RawBlocks.Get(n).decode(encoding="UTF-8", errors="ignore")))
        )
        print(
            "Block (showing raw hex data in block) ["
            + str(n)
            + "] : \n"
            + str((self.RawBlocks.Get(n).hex()))
        )
        return 0

    # implements showblockslice (log slice of block n contents)
    def showblockslice(self, n, start, end):
        try:
            n = int(n)
        except ValueError:
            print("Error: " + n + " not a valid Integer")
            return -1
        try:
            start = int(start)
        except ValueError:
            print("Error: " + start + " not a valid Integer")
            return -1
        try:
            end = int(end)
        except ValueError:
            print("Error: " + end + " not a valid Integer")
            return -1

        if n < 0 or n >= fsconfig.TOTAL_NUM_BLOCKS:
            print(
                "Error: block number "
                + str(n)
                + " not in valid range [0, "
                + str(fsconfig.TOTAL_NUM_BLOCKS - 1)
                + "]"
            )
            return -1
        if start < 0 or start >= fsconfig.BLOCK_SIZE:
            print(
                "Error: start "
                + str(start)
                + "not in valid range [0, "
                + str(fsconfig.BLOCK_SIZE - 1)
                + "]"
            )
            return -1
        if end < 0 or end >= fsconfig.BLOCK_SIZE or end <= start:
            print(
                "Error: end "
                + str(end)
                + "not in valid range [0, "
                + str(fsconfig.BLOCK_SIZE - 1)
                + "]"
            )
            return -1

        wholeblock = self.RawBlocks.Get(n)
        print(
            "Block (raw hex block) ["
            + str(n)
            + "] : \n"
            + str((wholeblock[start : end + 1].hex()))
        )
        return 0

    # file operations
    # implements cd (change directory)
    def cd(self, dir):
        self.RawBlocks.Acquire()
        i = self.AbsolutePathObject.PathNameToInodeNumber(dir, self.cwd)
        if i == -1:
            print("Error: not found\n")
            return -1
        inobj = InodeNumber(i)
        inobj.InodeNumberToInode(self.RawBlocks)
        if inobj.inode.type != fsconfig.INODE_TYPE_DIR:
            print("Error: not a directory\n")
            return -1
        self.cwd = i
        self.RawBlocks.Release()

    # implements ls (lists files in directory)
    def ls(self):
        self.RawBlocks.Acquire()
        inobj = InodeNumber(self.cwd)
        inobj.InodeNumberToInode(self.RawBlocks)
        block_index = 0
        while block_index <= (inobj.inode.size // fsconfig.BLOCK_SIZE):
            block = self.RawBlocks.Get(inobj.inode.block_numbers[block_index])
            if block_index == (inobj.inode.size // fsconfig.BLOCK_SIZE):
                end_position = inobj.inode.size % fsconfig.BLOCK_SIZE
            else:
                end_position = fsconfig.BLOCK_SIZE
            current_position = 0
            while current_position < end_position:
                entryname = block[
                    current_position : current_position + fsconfig.MAX_FILENAME
                ]
                entryinode = block[
                    current_position
                    + fsconfig.MAX_FILENAME : current_position
                    + fsconfig.FILE_NAME_DIRENTRY_SIZE
                ]
                entryinodenumber = int.from_bytes(entryinode, byteorder="big")
                inobj2 = InodeNumber(entryinodenumber)
                inobj2.InodeNumberToInode(self.RawBlocks)
                if inobj2.inode.type == fsconfig.INODE_TYPE_DIR:
                    print(
                        "[" + str(inobj2.inode.refcnt) + "]:" + entryname.decode() + "/"
                    )
                else:
                    if inobj2.inode.type == fsconfig.INODE_TYPE_SYM:
                        target_block_number = inobj2.inode.block_numbers[0]
                        target_block = self.RawBlocks.Get(target_block_number)
                        target_slice = target_block[0 : inobj2.inode.size]
                        print(
                            "["
                            + str(inobj2.inode.refcnt)
                            + "]:"
                            + entryname.decode()
                            + "@ -> "
                            + target_slice.decode()
                        )
                    else:
                        print(
                            "[" + str(inobj2.inode.refcnt) + "]:" + entryname.decode()
                        )
                current_position += fsconfig.FILE_NAME_DIRENTRY_SIZE
            block_index += 1
        self.RawBlocks.Release()
        return 0

    # implements cat (print file contents)
    def cat(self, filename):
        self.RawBlocks.Acquire()
        i = self.AbsolutePathObject.PathNameToInodeNumber(filename, self.cwd)
        if i == -1:
            print("Error: not found\n")
            return -1
        inobj = InodeNumber(i)
        inobj.InodeNumberToInode(self.RawBlocks)
        if inobj.inode.type != fsconfig.INODE_TYPE_FILE:
            print("Error: not a file\n")
            return -1
        data, errorcode = self.FileOperationsObject.Read(i, 0, fsconfig.MAX_FILE_SIZE)
        if data == -1:
            print("Error: " + errorcode)
            return -1
        print(data.decode())
        self.RawBlocks.Release()
        return 0

    # implements mkdir
    def mkdir(self, dir):
        self.RawBlocks.Acquire()
        i, errorcode = self.FileOperationsObject.Create(
            self.cwd, dir, fsconfig.INODE_TYPE_DIR
        )
        if i == -1:
            print("Error: " + errorcode + "\n")
            return -1
        self.RawBlocks.Release()
        return 0

    # implements create
    def create(self, file):
        self.RawBlocks.Acquire()
        i, errorcode = self.FileOperationsObject.Create(
            self.cwd, file, fsconfig.INODE_TYPE_FILE
        )
        if i == -1:
            print("Error: " + errorcode + "\n")
            return -1
        self.RawBlocks.Release()
        return 0

    # implements append
    def append(self, filename, string):
        self.RawBlocks.Acquire()
        i = self.AbsolutePathObject.PathNameToInodeNumber(filename, self.cwd)
        if i == -1:
            print("Error: not found\n")
            return -1
        inobj = InodeNumber(i)
        inobj.InodeNumberToInode(self.RawBlocks)
        if inobj.inode.type != fsconfig.INODE_TYPE_FILE:
            print("Error: not a file\n")
            return -1
        written, errorcode = self.FileOperationsObject.Write(
            i, inobj.inode.size, bytearray(string, "utf-8")
        )
        if written == -1:
            print("Error: " + errorcode)
            return -1
        print("Successfully appended " + str(written) + " bytes.")
        self.RawBlocks.Release()
        return 0

    # implements slice filename offset count ("slice off" contents from a file starting from offset and for count bytes)
    def slice(self, filename, offset, count):
        self.RawBlocks.Acquire()
        try:
            offset = int(offset)
        except ValueError:
            print("Error: " + offset + " not a valid Integer")
            return -1
        try:
            count = int(count)
        except ValueError:
            print("Error: " + count + " not a valid Integer")
            return -1
        i = self.AbsolutePathObject.PathNameToInodeNumber(filename, self.cwd)
        if i == -1:
            print("Error: not found\n")
            return -1
        inobj = InodeNumber(i)
        inobj.InodeNumberToInode(self.RawBlocks)
        if inobj.inode.type != fsconfig.INODE_TYPE_FILE:
            print("Error: not a file\n")
            return -1
        data, errorcode = self.FileOperationsObject.Slice(i, offset, count)
        if data == -1:
            print("Error: " + errorcode)
            return -1
        self.RawBlocks.Release()
        return 0

    # implements mirror filename (mirror the contents of a file)
    def mirror(self, filename):
        self.RawBlocks.Acquire()
        i = self.AbsolutePathObject.PathNameToInodeNumber(filename, self.cwd)
        if i == -1:
            print("Error: not found\n")
            return -1
        inobj = InodeNumber(i)
        inobj.InodeNumberToInode(self.RawBlocks)
        if inobj.inode.type != fsconfig.INODE_TYPE_FILE:
            print("Error: not a file\n")
            return -1
        data, errorcode = self.FileOperationsObject.Mirror(i)
        if data == -1:
            print("Error: " + errorcode)
            return -1
        self.RawBlocks.Release()
        return 0

    # implements rm
    def rm(self, filename):
        self.RawBlocks.Acquire()
        i, errorcode = self.FileOperationsObject.Unlink(self.cwd, filename)
        if i == -1:
            print("Error: " + errorcode + "\n")
            return -1
        self.RawBlocks.Release()
        return 0

    # implements hard link
    def lnh(self, target, name):
        self.RawBlocks.Acquire()
        i, errorcode = self.AbsolutePathObject.Link(target, name, self.cwd)
        if i == -1:
            print("Error: " + errorcode)
            return -1
        self.RawBlocks.Release()
        return 0

    # implements soft link
    def lns(self, target, name):
        self.RawBlocks.Acquire()
        i, errorcode = self.AbsolutePathObject.Symlink(target, name, self.cwd)
        if i == -1:
            print("Error: " + errorcode)
            return -1
        self.RawBlocks.Release()
        return 0

    ## Main interpreter loop
    def Interpreter(self):
        while True:
            command = input("[cwd=" + str(self.cwd) + "]%")
            splitcmd = command.split()
            if len(splitcmd) == 0:
                continue
            elif splitcmd[0] == "cd":
                if len(splitcmd) != 2:
                    print("Error: cd requires one argument")
                else:
                    self.cd(splitcmd[1])
            elif splitcmd[0] == "cat":
                if len(splitcmd) != 2:
                    print("Error: cat requires one argument")
                else:
                    self.cat(splitcmd[1])
            elif splitcmd[0] == "ls":
                self.ls()
            elif splitcmd[0] == "showblock":
                if len(splitcmd) != 2:
                    print("Error: showblock requires one argument")
                else:
                    self.showblock(splitcmd[1])
            elif splitcmd[0] == "showblockslice":
                if len(splitcmd) != 4:
                    print("Error: showblockslice requires three arguments")
                else:
                    self.showblockslice(splitcmd[1], splitcmd[2], splitcmd[3])
            elif splitcmd[0] == "showinode":
                if len(splitcmd) != 2:
                    print("Error: showinode requires one argument")
                else:
                    self.showinode(splitcmd[1])
            elif splitcmd[0] == "showfsconfig":
                if len(splitcmd) != 1:
                    print("Error: showfsconfig do not require argument")
                else:
                    self.showfsconfig()
            elif splitcmd[0] == "load":
                if len(splitcmd) != 2:
                    print("Error: load requires 1 argument")
                else:
                    self.load(splitcmd[1])
            elif splitcmd[0] == "save":
                if len(splitcmd) != 2:
                    print("Error: save requires 1 argument")
                else:
                    self.save(splitcmd[1])
            elif splitcmd[0] == "mkdir":
                if len(splitcmd) != 2:
                    print("Error: mkdir requires one argument")
                else:
                    self.mkdir(splitcmd[1])
            elif splitcmd[0] == "create":
                if len(splitcmd) != 2:
                    print("Error: create requires one argument")
                else:
                    self.create(splitcmd[1])
            elif splitcmd[0] == "append":
                if len(splitcmd) != 3:
                    print("Error: append requires two arguments")
                else:
                    self.append(splitcmd[1], splitcmd[2])
            elif splitcmd[0] == "slice":
                if len(splitcmd) != 4:
                    print("Error: slice requires three arguments")
                else:
                    self.slice(splitcmd[1], splitcmd[2], splitcmd[3])
            elif splitcmd[0] == "mirror":
                if len(splitcmd) != 2:
                    print("Error: mirror requires one argument")
                else:
                    self.mirror(splitcmd[1])
            elif splitcmd[0] == "rm":
                if len(splitcmd) != 2:
                    print("Error: rm requires one argument")
                else:
                    self.rm(splitcmd[1])
            elif splitcmd[0] == "lnh":
                if len(splitcmd) != 3:
                    print("Error: lnh requires two arguments")
                else:
                    self.lnh(splitcmd[1], splitcmd[2])
            elif splitcmd[0] == "lns":
                if len(splitcmd) != 3:
                    print("Error: lns requires two arguments")
                else:
                    self.lns(splitcmd[1], splitcmd[2])
            elif splitcmd[0] == "exit":
                return
            else:
                print("command " + splitcmd[0] + " not valid.\n")
