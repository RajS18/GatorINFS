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
    
  def Link(self,cwd,target,name):
    logging.debug("AbsolutePathName::Link: hard-link: " + str(name) + ", dir: " + str(cwd))

    target_inode_number = self.GeneralPathToInodeNumber(target, cwd)
    #target file/dir is absent.
    if target_inode_number == -1:
        return -1,"ERROR_LINK_TARGET_DOESNOT_EXIST"
    target_inode_instance = InodeNumber(target_inode_number)
    target_inode_instance.InodeNumberToInode(self.FileNameObject.RawBlocks)
    # Check if cwd is a directory
    cwd_inode_instance = InodeNumber(cwd)
    cwd_inode_instance.InodeNumberToInode(self.FileNameObject.RawBlocks)
    if cwd_inode_instance.inode.type == fsconfig.INODE_TYPE_FILE:
        return -1,"ERROR_LINK_NOT_DIRECTORY"
    #Not enough space
    end_position = self.FileNameObject.FindAvailableFileEntry(cwd)
    if end_position == -1:
      return -1,"ERROR_LINK_DATA_BLOCK_NOT_AVAILABLE"
    # linkname = name is already present in the cwd.
    lookup_inode = self.FileNameObject.Lookup(name,cwd)
    if lookup_inode != -1:
      return -1,"ERROR_LINK_ALREADY_EXIST"
    
    if target_inode_instance.inode.type != fsconfig.INODE_TYPE_FILE:
      return -1,"ERROR_LINK_TARGET_NOT_FILE"
    
    self.FileNameObject.InsertFilenameInodeNumber(cwd_inode_instance, name, target_inode_number)
    target_inode_instance.inode.refcnt += 1
    target_inode_instance.StoreInode(self.FileNameObject.RawBlocks)
    return 0,"SUCCESS"
    
  def SymLink(self,cwd, target, name):
    logging.debug("AbsolutePathName::SymLink: soft-link: " + str(name) + ", dir: " + str(cwd))

    target_inode_number = self.GeneralPathToInodeNumber(target, cwd)
    #target file/dir is absent.
    if target_inode_number == -1:
        return -1,"ERROR_SYMLINK_TARGET_DOESNOT_EXIST"
    
    target_inode_instance = InodeNumber(target_inode_number)
    target_inode_instance.InodeNumberToInode(self.FileNameObject.RawBlocks)
    # Check if cwd is a directory
    cwd_inode_instance = InodeNumber(cwd)
    cwd_inode_instance.InodeNumberToInode(self.FileNameObject.RawBlocks)
    if cwd_inode_instance.inode.type == fsconfig.INODE_TYPE_FILE:
        return -1,"ERROR_SYMLINK_NOT_DIRECTORY"
    #Not enough space
    end_position = self.FileNameObject.FindAvailableFileEntry(cwd)
    if end_position == -1:
      return -1,"ERROR_SYMLINK_DATA_BLOCK_NOT_AVAILABLE"
    # symlinkname = name is already present in the cwd.
    lookup_inode = self.FileNameObject.Lookup(name,cwd)
    if lookup_inode != -1:
      return -1,"ERROR_SYMLINK_ALREADY_EXIST"
    
    #no more inodes to store the virtua link
    available_inode_n = self.FileNameObject.FindAvailableInode()
    if available_inode_n == -1:
      return -1,"ERROR_SYMLINK_INODE_NOT_AVAILABLE"
    
    #link name exceeds the single block size.
    stringbyte = bytearray(target,"utf-8")
    if len(stringbyte)>fsconfig.BLOCK_SIZE:
      return -1,"ERROR_SYMLINK_TARGET_EXCEEDS_BLOCK_SIZE"
    
    available_inode_number = InodeNumber(available_inode_n)
    available_inode_number.InodeNumberToInode(self.FileNameObject.RawBlocks)
    #this inode must showcase type=symbolic link
    available_inode_number.inode.type = fsconfig.INODE_TYPE_SYM
    available_inode_number.inode.refcnt = 1
    available_inode_number.inode.block_numbers[0] = self.FileNameObject.AllocateDataBlock()
    start = 0
    end = len(stringbyte)%fsconfig.BLOCK_SIZE
    bytes_written = end - start
    available_inode_number.inode.size = bytes_written

    block_number = available_inode_number.inode.block_numbers[0]
    available_inode_number.StoreInode(self.FileNameObject.RawBlocks)
    block = self.FileNameObject.RawBlocks.Get(block_number)
    block[start:end] = stringbyte
    self.FileNameObject.RawBlocks.Put(block_number, block)
    

    self.FileNameObject.InsertFilenameInodeNumber(cwd_inode_instance, name, available_inode_n)


    target_inode_instance.inode.refcnt += 1
    target_inode_instance.StoreInode(self.FileNameObject.RawBlocks)
    return 0,"SUCCESS"
  
  def PathNameToInodeNumber(self, cwd, pathName):
    i = self.GeneralPathToInodeNumber(pathName, cwd)
    inode_ = InodeNumber(i)
    inode_.InodeNumberToInode(self.FileNameObject.RawBlocks)
    if inode_.inode.type == fsconfig.INODE_TYPE_FILE:
      return i,0
    elif inode_.inode.type == fsconfig.INODE_TYPE_DIR:
      return i,1
    return -1,-1

    
