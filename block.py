import pickle, logging
import fsconfig
import xmlrpc.client, socket, time
import time

#### BLOCK LAYER

# global TOTAL_NUM_BLOCKS, BLOCK_SIZE, INODE_SIZE, MAX_NUM_INODES, MAX_FILENAME, INODE_NUMBER_DIRENTRY_SIZE


class DiskBlocks:
    def __init__(self):
        self.cache = {}
        # initialize clientID
        if fsconfig.CID >= 0 and fsconfig.CID < fsconfig.MAX_CLIENTS:
            self.clientID = fsconfig.CID
        else:
            print("Must specify valid cid")
            quit()

        # initialize XMLRPC client connection to raw block server
        if fsconfig.PORT:
            PORT = fsconfig.PORT
        else:
            print("Must specify port number")
            quit()
        server_url = "http://" + fsconfig.SERVER_ADDRESS + ":" + str(PORT)
        # print(server_url)
        self.block_server = xmlrpc.client.ServerProxy(
            server_url, use_builtin_types=True
        )
        socket.setdefaulttimeout(fsconfig.SOCKET_TIMEOUT)

    ## Put: interface to write a raw block of data to the block indexed by block number
    ## Blocks are padded with zeroes up to BLOCK_SIZE

    def Put(self, block_number, block_data):
        while True:
            try:
                logging.debug(
                    "Put: block number "
                    + str(block_number)
                    + " len "
                    + str(len(block_data))
                    + "\n"
                    + str(block_data.hex())
                )
                if len(block_data) > fsconfig.BLOCK_SIZE:
                    logging.error(
                        "Put: Block larger than BLOCK_SIZE: " + str(len(block_data))
                    )
                    quit()
                if block_number in range(0, fsconfig.TOTAL_NUM_BLOCKS):
                    _cid = self.clientID.to_bytes(1, byteorder="big")
                    set_cid = bytearray(_cid.ljust(fsconfig.BLOCK_SIZE, b"\x00"))
                    self.block_server.Put(fsconfig.TOTAL_NUM_BLOCKS - 2, set_cid)
                    # ljust does the padding with zeros
                    putdata = bytearray(block_data.ljust(fsconfig.BLOCK_SIZE, b"\x00"))
                    # Write block
                    # commenting this out as the request now goes to the server
                    # self.block[block_number] = putdata
                    # call Put() method on the server; code currently quits on any server failure
                    ret = self.block_server.Put(block_number, putdata)
                    if ret == -1:
                        logging.error("Put: Server returns error")
                        quit()
                    if block_number < fsconfig.TOTAL_NUM_BLOCKS - 2:
                        self.cache[block_number] = putdata
                        print("CACHE_WRITE_THROUGH " + str(block_number))
                    return 0
                else:
                    logging.error("Put: Block out of range: " + str(block_number))
                    quit()
            except (socket.timeout, xmlrpc.client.Fault, ConnectionRefusedError) as e:
                print("SERVER_TIMED_OUT")
                time.sleep(fsconfig.RETRY_INTERVAL)

    ## Get: interface to read a raw block of data from block indexed by block number
    ## Equivalent to the textbook's BLOCK_NUMBER_TO_BLOCK(b)

    def Get(self, block_number):
        while True:
            try:
                logging.debug("Get: " + str(block_number))
                if block_number in range(0, fsconfig.TOTAL_NUM_BLOCKS):
                    if block_number in self.cache:
                        print("CACHE_HIT " + str(block_number))
                        return self.cache[block_number]

                    # logging.debug ('\n' + str((self.block[block_number]).hex()))
                    # commenting this out as the request now goes to the server
                    # return self.block[block_number]
                    # call Get() method on the server
                    data = self.block_server.Get(block_number)
                    # return as bytearray
                    if block_number < fsconfig.TOTAL_NUM_BLOCKS - 2:
                        print("CACHE_MISS " + str(block_number))
                        self.cache[block_number] = bytearray(data)
                    return bytearray(data)

                logging.error(
                    "DiskBlocks::Get: Block number larger than TOTAL_NUM_BLOCKS: "
                    + str(block_number)
                )
                quit()
            except (socket.timeout, xmlrpc.client.Fault, ConnectionRefusedError) as e:
                print("SERVER_TIMED_OUT")
                time.sleep(fsconfig.RETRY_INTERVAL)

    ## Serializes and saves the DiskBlocks block[] data structure to a "dump" file on your disk

    def DumpToDisk(self, filename):
        logging.info(
            "DiskBlocks::DumpToDisk: Dumping pickled blocks to file " + filename
        )
        file = open(filename, "wb")
        file_system_constants = (
            "BS_"
            + str(fsconfig.BLOCK_SIZE)
            + "_NB_"
            + str(fsconfig.TOTAL_NUM_BLOCKS)
            + "_IS_"
            + str(fsconfig.INODE_SIZE)
            + "_MI_"
            + str(fsconfig.MAX_NUM_INODES)
            + "_MF_"
            + str(fsconfig.MAX_FILENAME)
            + "_IDS_"
            + str(fsconfig.INODE_NUMBER_DIRENTRY_SIZE)
        )
        pickle.dump(file_system_constants, file)
        # pickle.dump(self.block, file)

        file.close()

    ## Loads DiskBlocks block[] data structure from a "dump" file on your disk

    def LoadFromDump(self, filename):
        logging.info(
            "DiskBlocks::LoadFromDump: Reading blocks from pickled file " + filename
        )
        file = open(filename, "rb")
        file_system_constants = (
            "BS_"
            + str(fsconfig.BLOCK_SIZE)
            + "_NB_"
            + str(fsconfig.TOTAL_NUM_BLOCKS)
            + "_IS_"
            + str(fsconfig.INODE_SIZE)
            + "_MI_"
            + str(fsconfig.MAX_NUM_INODES)
            + "_MF_"
            + str(fsconfig.MAX_FILENAME)
            + "_IDS_"
            + str(fsconfig.INODE_NUMBER_DIRENTRY_SIZE)
        )

        try:
            read_file_system_constants = pickle.load(file)
            if file_system_constants != read_file_system_constants:
                print(
                    "DiskBlocks::LoadFromDump Error: File System constants of File :"
                    + read_file_system_constants
                    + " do not match with current file system constants :"
                    + file_system_constants
                )
                return -1
            block = pickle.load(file)
            for i in range(0, fsconfig.TOTAL_NUM_BLOCKS):
                self.Put(i, block[i])
            return 0
        except TypeError:
            print(
                "DiskBlocks::LoadFromDump: Error: File not in proper format, encountered type error "
            )
            return -1
        except EOFError:
            print(
                "DiskBlocks::LoadFromDump: Error: File not in proper format, encountered EOFError error "
            )
            return -1
        finally:
            file.close()

    ## Prints to screen block contents, from min to max

    def PrintBlocks(self, tag, min, max):
        print("#### Raw disk blocks: " + tag)
        for i in range(min, max):
            print("Block [" + str(i) + "] : " + str((self.Get(i)).hex()))

    def Acquire(self):
        while True:
            try:
                status = self.block_server.Get(fsconfig.TOTAL_NUM_BLOCKS - 1).hex()[0:2]
                if int(status, 16) == 0:
                    print("CACHE_MISS " + str(fsconfig.TOTAL_NUM_BLOCKS - 2))
                    server_cid = self.Get(fsconfig.TOTAL_NUM_BLOCKS - 2).hex()[0:2]
                    if int(server_cid, 16) != self.clientID:
                        print("CACHE_INVALIDATED")
                        self.CheckAndInvalidateCache()
                        _cid = self.clientID.to_bytes(1, byteorder="big")
                        set_cid = bytearray(_cid.ljust(fsconfig.BLOCK_SIZE, b"\x00"))
                        self.Put(fsconfig.TOTAL_NUM_BLOCKS - 2, set_cid)
                        print(
                            "CACHE_WRITE_THROUGH {}".format(
                                fsconfig.TOTAL_NUM_BLOCKS - 2
                            )
                        )
                    self.RSM()
                    break

            except (socket.timeout, xmlrpc.client.Fault, ConnectionRefusedError) as e:
                print("SERVER_TIMED_OUT")
                time.sleep(fsconfig.RETRY_INTERVAL)

    def Release(self):
        # not sure about the keeping this in a loop
        while True:
            try:
                RSM_UNLOCKED = bytearray(b"\x00") * 1
                data = bytearray(RSM_UNLOCKED.ljust(fsconfig.BLOCK_SIZE, b"\x00"))
                self.block_server.Put(fsconfig.TOTAL_NUM_BLOCKS - 1, data)
                print("CACHE_WRITE_THROUGH " + str(fsconfig.TOTAL_NUM_BLOCKS - 1))
                break
            except (socket.timeout, xmlrpc.client.Fault, ConnectionRefusedError) as e:
                print("SERVER_TIMED_OUT")
                time.sleep(fsconfig.RETRY_INTERVAL)

    def RSM(self):
        self.block_server.RSM(fsconfig.TOTAL_NUM_BLOCKS - 1)

    def CheckAndInvalidateCache(self):
        self.cache.clear()
