import fsconfig
import logging
from block import *
from inode import *
from inodenumber import *
from filename import *

## This class implements methods for absolute path layer

class AbsolutePathName():
  def __init__(self, FileNameObject):
    self.FileNameObject = FileNameObject

  def PathToInodeNumber(self, path, dir):

    logging.debug("AbsolutePathName::PathToInodeNumber: path: " + str(path) + ", dir: " + str(dir))

    if "/" in path:
      split_path = path.split("/")
      first = split_path[0]
      del split_path[0]
      rest = "/".join(split_path)
      logging.debug("AbsolutePathName::PathToInodeNumber: first: " + str(first) + ", rest: " + str(rest))
      d = self.FileNameObject.Lookup(first, dir)
      if d == -1:
        return -1
      return self.PathToInodeNumber(rest, d)
    else:
      return self.FileNameObject.Lookup(path, dir)


  def GeneralPathToInodeNumber(self, path, cwd):

    logging.debug ("AbsolutePathName::GeneralPathToInodeNumber: path: " + str(path) + ", cwd: " + str(cwd))

    if path[0] == "/":
      if len(path) == 1: # special case: root
        logging.debug ("AbsolutePathName::GeneralPathToInodeNumber: returning root inode 0")
        return 0
      cut_path = path[1:len(path)]
      logging.debug ("AbsolutePathName::GeneralPathToInodeNumber: cut_path: " + str(cut_path))
      return self.PathToInodeNumber(cut_path,0)
    else:
      return self.PathToInodeNumber(path,cwd)


# BEGIN_REMOVE_TO_DISTRIBUTE
  def PathNameToInodeNumber(self, path, cwd):

    # resolves soft links; see textbook p. 105

    logging.debug ("AbsolutePathName::PathNameToInodeNumber: path: " + str(path) + ", cwd: " + str(cwd))

    i = self.GeneralPathToInodeNumber(path, cwd)
    lookedup_inode = InodeNumber(i)
    lookedup_inode.InodeNumberToInode(self.FileNameObject.RawBlocks)

    if lookedup_inode.inode.type == fsconfig.INODE_TYPE_SYM:
      logging.debug ("AbsolutePathName::PathNameToInodeNumber: inode is symlink: " + str(i))
      # read block with target string from RawBlocks
      block_number = lookedup_inode.inode.block_numbers[0]
      block = self.FileNameObject.RawBlocks.Get(block_number)
      # extract slice with length of target string
      target_slice = block[0:lookedup_inode.inode.size]
      rest = target_slice.decode()
      logging.debug ("AbsolutePathName::PathNameToInodeNumber: rest: " + rest)
      i = self.GeneralPathToInodeNumber(rest, cwd)

    return i


  def Link(self, target, name, cwd):

    logging.debug ("AbsolutePathName::Link: target: " + str(target) + ", name: " + str(name) + ", cwd: " + str(cwd))

    target_inode_number = self.PathNameToInodeNumber(target, cwd)
    if target_inode_number == -1:
      logging.debug ("AbsolutePathName::Link: target does not exist")
      return -1, "ERROR_LINK_TARGET_DOESNOT_EXIST"

    cwd_inode = InodeNumber(cwd)
    cwd_inode.InodeNumberToInode(self.FileNameObject.RawBlocks)
    if cwd_inode.inode.type != fsconfig.INODE_TYPE_DIR:
      logging.debug ("AbsolutePathName::Link: cwd is not a directory")
      return -1, "ERROR_LINK_NOT_DIRECTORY"

    # Find available slot in directory data block
    fileentry_position = self.FileNameObject.FindAvailableFileEntry(cwd)
    if fileentry_position == -1:
      logging.debug ("AbsolutePathName::Link: no entry available for another link")
      return -1, "ERROR_LINK_DATA_BLOCK_NOT_AVAILABLE"

    # Ensure it's not a duplicate - if Lookup returns anything other than -1
    if self.FileNameObject.Lookup(name, cwd) != -1:
      logging.debug ("AbsolutePathName::Link: name already exists")
      return -1, "ERROR_LINK_ALREADY_EXISTS"

    # Ensure target is a file
    target_obj = InodeNumber(target_inode_number)
    target_obj.InodeNumberToInode(self.FileNameObject.RawBlocks)
    if target_obj.inode.type != fsconfig.INODE_TYPE_FILE:
      logging.debug ("AbsolutePathName::Link: target must be a file")
      return -1, "ERROR_LINK_TARGET_NOT_FILE"

    # Add to directory (filename,inode) table
    self.FileNameObject.InsertFilenameInodeNumber(cwd_inode, name, target_inode_number)

    # Update refcnt of target and write to file system
    target_inode_number_object = InodeNumber(target_inode_number)
    target_inode_number_object.InodeNumberToInode(self.FileNameObject.RawBlocks)
    target_inode_number_object.inode.refcnt += 1
    target_inode_number_object.StoreInode(self.FileNameObject.RawBlocks)

    # Update refcnt of directory and write to file system
    cwd_inode.inode.refcnt += 1
    cwd_inode.StoreInode(self.FileNameObject.RawBlocks)

    return 0, "SUCCESS"

  def Symlink(self, target, name, cwd):

    logging.debug ("AbsolutePathName::Symlink: target: " + str(target) + ", name: " + str(name) + ", cwd: " + str(cwd))

    target_inode_number = self.PathNameToInodeNumber(target, cwd)
    if target_inode_number == -1:
      logging.debug ("AbsolutePathName::Symlink: target does not exist")
      return -1, "ERROR_SYMLINK_TARGET_DOESNOT_EXIST"

    cwd_inode = InodeNumber(cwd)
    cwd_inode.InodeNumberToInode(self.FileNameObject.RawBlocks)
    if cwd_inode.inode.type != fsconfig.INODE_TYPE_DIR:
      logging.debug ("AbsolutePathName::Symlink: cwd is not a directory")
      return -1, "ERROR_SYMLINK_NOT_DIRECTORY"

    # Find available slot in directory data block
    fileentry_position = self.FileNameObject.FindAvailableFileEntry(cwd)
    if fileentry_position == -1:
      logging.debug ("AbsolutePathName::Symlink: no entry available for another link")
      return -1, "ERROR_SYMLINK_DATA_BLOCK_NOT_AVAILABLE"

    # Ensure it's not a duplicate - if Lookup returns anything other than -1
    if self.FileNameObject.Lookup(name, cwd) != -1:
      logging.debug ("AbsolutePathName::Symlink: name already exists")
      return -1, "ERROR_SYMLINK_ALREADY_EXISTS"

    # Find if there is an available inode
    inode_position = self.FileNameObject.FindAvailableInode()
    if inode_position == -1:
      logging.debug ("ERROR_SYMLINK_INODE_NOT_AVAILABLE")
      return -1, "ERROR_SYMLINK_INODE_NOT_AVAILABLE"

    # ensure target size fits in a block
    if len(target) > fsconfig.BLOCK_SIZE:
      logging.debug ("ERROR_SYMLINK_TARGET_EXCEEDS_BLOCK_SIZE ")
      return -1, "ERROR_SYMLINK_TARGET_EXCEEDS_BLOCK_SIZE"

    # Create new Inode for symlink
    symlink_inode = InodeNumber(inode_position)
    symlink_inode.InodeNumberToInode(self.FileNameObject.RawBlocks)
    symlink_inode.inode.type = fsconfig.INODE_TYPE_SYM
    symlink_inode.inode.size = len(target)
    symlink_inode.inode.refcnt = 1

    # Allocate one data block and set as first entry in block_numbers[]
    symlink_inode.inode.block_numbers[0] = self.FileNameObject.AllocateDataBlock()
    symlink_inode.StoreInode(self.FileNameObject.RawBlocks)

    # Add to directory's (filename,inode) table
    self.FileNameObject.InsertFilenameInodeNumber(cwd_inode, name, inode_position)

    # Write target path to block
    # first, we read the whole block from raw storage
    block_number = symlink_inode.inode.block_numbers[0]
    block = self.FileNameObject.RawBlocks.Get(block_number)
    # copy slice of data into the right position in the block
    stringbyte = bytearray(target,"utf-8")
    block[0:len(target)] = stringbyte
    # now write modified block back to disk
    self.FileNameObject.RawBlocks.Put(block_number,block)

    # Update refcnt of directory and write to file system
    cwd_inode.inode.refcnt += 1
    cwd_inode.StoreInode(self.FileNameObject.RawBlocks)

    return 0, "SUCCESS"


# END_REMOVE_TO_DISTRIBUTE
