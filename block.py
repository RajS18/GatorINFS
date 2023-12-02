import pickle, logging
import fsconfig
import xmlrpc.client, socket, time

#### BLOCK LAYER

# global TOTAL_NUM_BLOCKS, BLOCK_SIZE, INODE_SIZE, MAX_NUM_INODES, MAX_FILENAME, INODE_NUMBER_DIRENTRY_SIZE

class DiskBlocks():
    def __init__(self):
        # initialize clientID
        if fsconfig.CID >= 0 and fsconfig.CID < fsconfig.MAX_CLIENTS:
            self.clientID = fsconfig.CID
        else:
            print('Must specify valid cid')
            quit()
        self.server_list = []
        # initialize XMLRPC client connection to raw block server
        if fsconfig.PORT:
            PORT = fsconfig.PORT
        else:
            print('Must specify port number')
            quit()
        for i in range (0,fsconfig.NUM_SERVERS):
            server_url = 'http://' + fsconfig.SERVER_ADDRESS + ':' + str(PORT+i)
            self.server_list.append(xmlrpc.client.ServerProxy(server_url,use_builtin_types=True))
        #server_url = 'http://' + fsconfig.SERVER_ADDRESS + ':' + str(PORT)
        #self.block_server = xmlrpc.client.ServerProxy(server_url, use_builtin_types=True)
        socket.setdefaulttimeout(fsconfig.SOCKET_TIMEOUT)
        # initialize block cache empty
        self.bcache = []
        for i in range(fsconfig.NUM_SERVERS):
            self.bcache.append({})

    ## Put: interface to write a raw block of data to the block indexed by block number
    ## Blocks are padded with zeroes up to BLOCK_SIZE

    def Put(self, block_number, block_data):

        logging.debug(
            'Put: block number ' + str(block_number) + ' len ' + str(len(block_data)) + '\n' + str(block_data.hex()))
        if len(block_data) > fsconfig.BLOCK_SIZE:
            logging.error('Put: Block larger than BLOCK_SIZE: ' + str(len(block_data)))
            quit()

        if block_number in range(0, fsconfig.TOTAL_NUM_BLOCKS):
            # ljust does the padding with zeros
            parity_server_number = (block_number//(fsconfig.NUM_SERVERS-1))%fsconfig.NUM_SERVERS  #parity server number
            parity_level = block_number//(fsconfig.NUM_SERVERS-1)                                #parity level
            data_block_level = block_number//(fsconfig.NUM_SERVERS-1)                             #data_block level
            server_number = block_number%(fsconfig.NUM_SERVERS-1)                                   #level for data_block
            if server_number >= (data_block_level%fsconfig.NUM_SERVERS):
                server_number+=1
            
            putdata = bytearray(block_data.ljust(fsconfig.BLOCK_SIZE, b'\x00'))
            self.bcache[server_number][data_block_level] = putdata
            
            # Write block

            # commenting this out as the request now goes to the server
            # self.block[block_number] = putdata
            # call Put() method on the server; code currently quits on any server failure
            rpcretry = True
            while rpcretry:
                rpcretry = False
                try:
                    self.server_list[server_number].Put(data_block_level,putdata)
                except (socket.timeout, ConnectionRefusedError ,xmlrpc.client.ProtocolError) as err:
                    
                    if err == socket.timeout:
                        print("SERVER_TIMED_OUT")
                        time.sleep(fsconfig.RETRY_INTERVAL)
                        rpcretry = True
                    else:
                        print("DISCONNECTED PUT SERVER NUMBER: ",str(server_number))
            #PARITY UPDATE
            rpcretry = True
            while rpcretry:
                rpcretry = False
                try:
                    curr_parity_data = self.Get(parity_level, parity_server_number)
                    par_result = bytearray(a ^ b for a, b in zip(curr_parity_data, putdata))
                    self.server_list[parity_server_number].Put(parity_level ,par_result)
                except (socket.timeout, ConnectionRefusedError ,xmlrpc.client.ProtocolError) as err:
                    
                    if err == socket.timeout:
                        print("SERVER_TIMED_OUT")
                        time.sleep(fsconfig.RETRY_INTERVAL)
                        rpcretry = True
                    else:
                        print("DISCONNECTED PUT SERVER NUMBER: ",str(parity_server_number))
            # update block cache
            if fsconfig.LOGCACHE == 1: print('CACHE_WRITE_THROUGH ' + str(block_number))

            
            
            # flag this s the last writer
            # unless this is a release - which doesn't flag last writer
            if block_number != fsconfig.TOTAL_NUM_BLOCKS-1:
                LAST_WRITER_BLOCK = fsconfig.TOTAL_NUM_BLOCKS - 2
                lwb_parity_server_number = (LAST_WRITER_BLOCK//(fsconfig.NUM_SERVERS-1))%fsconfig.NUM_SERVERS  #parity server number
                lwb_parity_level = LAST_WRITER_BLOCK//(fsconfig.NUM_SERVERS-1)                                 #parity level
                lwb_data_block_level = LAST_WRITER_BLOCK//(fsconfig.NUM_SERVERS-1)                             #data_block level
                lwb_server_number = LAST_WRITER_BLOCK % (fsconfig.NUM_SERVERS-1)                                   #level for data_block
                if lwb_server_number >= (lwb_data_block_level%fsconfig.NUM_SERVERS):
                    lwb_server_number+=1

                updated_block = bytearray(fsconfig.BLOCK_SIZE)
                updated_block[0] = fsconfig.CID
                
                rpcretry = True
                while rpcretry:
                    rpcretry = False
                    try:
                        self.server_list[lwb_server_number].Put(lwb_data_block_level, updated_block)
                    except (socket.timeout,ConnectionRefusedError, xmlrpc.client.ProtocolError) as err:
                        
                        if err == socket.timeout:
                            print("SERVER_TIMED_OUT")
                            time.sleep(fsconfig.RETRY_INTERVAL)
                            rpcretry = True

                        else:
                            print("DISCONNECTED PUT SERVER NUMBER: ", str(lwb_server_number))
                
                rpcretry = True
                while rpcretry:
                    rpcretry = False
                    try:
                        curr_parity_data = self.Get(lwb_parity_level, lwb_parity_server_number)
                        par_result = bytearray(a ^ b for a, b in zip(curr_parity_data, updated_block))
                        self.server_list[lwb_parity_server_number].Put(lwb_parity_level ,par_result)
                    except (socket.timeout,ConnectionRefusedError, xmlrpc.client.ProtocolError) as err:
                        
                        if err == socket.timeout:
                            print("SERVER_TIMED_OUT")
                            time.sleep(fsconfig.RETRY_INTERVAL)
                            rpcretry = True

                        else:
                            print("DISCONNECTED PUT SERVER NUMBER: ", str(parity_server_number))
                
            return 0
        else:
            logging.error('Put: Block out of range: ' + str(block_number))
            quit()


    ## Get: interface to read a raw block of data from block indexed by block number
    ## Equivalent to the textbook's BLOCK_NUMBER_TO_BLOCK(b)

    def Get(self, block_number, server_number = None):

        logging.debug('Get: ' + str(block_number))

        if block_number in range(0, fsconfig.TOTAL_NUM_BLOCKS):
            # logging.debug ('\n' + str((self.block[block_number]).hex()))
            # commenting this out as the request now goes to the server
            # return self.block[block_number]
            # call Get() method on the server
            # don't look up cache for last two blocks
            data=None
            if server_number == None:
                get_block_number = block_number//(fsconfig.NUM_SERVERS-1)                             #data_block level
                get_target_server_number = block_number%(fsconfig.NUM_SERVERS-1)                                   #level for data_block
                if get_target_server_number >= (get_block_number% fsconfig.NUM_SERVERS):
                    get_target_server_number+=1
                block_number = get_block_number
                server_number = get_target_server_number
            if (block_number < fsconfig.TOTAL_NUM_BLOCKS-2) and (block_number in self.bcache[server_number]):
                if fsconfig.LOGCACHE == 1: print('CACHE_HIT '+ str(block_number))
                data = self.bcache[server_number][block_number]
            else:
                if fsconfig.LOGCACHE == 1: print('CACHE_MISS ' + str(block_number))
                rpcretry = True
                while rpcretry:
                    rpcretry = False
                    try:
                        data = self.server_list[server_number].Get(block_number)
                        break
                    except (socket.timeout, xmlrpc.client.ProtocolError, ConnectionRefusedError) as err:
                        
                        if err == socket.timeout:
                            print("SERVER_TIMED_OUT")
                            time.sleep(fsconfig.RETRY_INTERVAL)
                            rpcretry = True
                        else:
                            print("DISCONNECTED GET SERVER NUMBER: ",server_number)
                            ret = bytearray(fsconfig.BLOCK_SIZE)
                            for i in range(fsconfig.NUM_SERVERS):
                                if i==server_number:
                                    continue
                                curr_data = self.Get(block_number,i)
                                ret = bytearray(a ^ b for a, b in zip(ret, curr_data))
                            data = ret
                # add to cache
                self.bcache[server_number][block_number] = data
            # return as bytearray
            return bytearray(data)

        logging.error('DiskBlocks::Get: Block number larger than TOTAL_NUM_BLOCKS: ' + str(block_number))
        quit()

## Repair procedure:
    def repair(self, server_number):
        logging.debug('Repair: by RAID 5' + str(server_number))
        # helper_server = -1
        # for server in range(0,fsconfig.NUM_SERVERS):
        #     if server!=server_number:
        #         helper_server=server
        #         break
        # for blockno in range(0,fsconfig.TOTAL_NUM_BLOCKS):
        #     data = self.server_list[helper_server].Get(blockno)
        #     self.server_list[server_number].Put(blockno,data)
        for levels in range(0,(fsconfig.TOTAL_NUM_BLOCKS//(fsconfig.NUM_SERVERS-1))  ):
            data = bytearray(fsconfig.BLOCK_SIZE)
            for i in range(0,fsconfig.NUM_SERVERS):
                if i==server_number:
                    continue
                curr_data = self.Get(levels,i)
                data = bytearray(a ^ b for a, b in zip(data, curr_data))

            self.server_list[server_number].Put(levels,data)

        return
## RSM: read and set memory equivalent

    def RSM(self, block_number):
        logging.debug('RSM: ' + str(block_number))
        
        if block_number in range(0, fsconfig.TOTAL_NUM_BLOCKS):
            rsm_block_number = block_number//(fsconfig.NUM_SERVERS-1)                             #data_block level
            rsm_server_number = block_number%(fsconfig.NUM_SERVERS-1)                                   #level for data_block
            if rsm_server_number >=( rsm_block_number%(fsconfig.NUM_SERVERS)):
                rsm_server_number+=1
            rpcretry = True
            while rpcretry:
                rpcretry = False
                try:
                    data = self.server_list[rsm_server_number].RSM(rsm_block_number)
                except (socket.timeout, ConnectionRefusedError, xmlrpc.client.ProtocolError) as err:
                    
                    if err == socket.timeout:
                        print("SERVER_TIMED_OUT")
                        time.sleep(fsconfig.RETRY_INTERVAL)
                        rpcretry = True
                    else:
                        print("DISCONNECTED RSM SERVER NUMBER: ", str(rsm_server_number))
                    
            return bytearray(data)

        logging.error('RSM: Block number larger than TOTAL_NUM_BLOCKS: ' + str(rsm_block_number))
        quit()



        ## Acquire and Release using a disk block lock

    def Acquire(self):
        logging.debug('Acquire')
        RSM_BLOCK = fsconfig.TOTAL_NUM_BLOCKS - 1
        lockvalue = self.RSM(RSM_BLOCK)
        logging.debug("RSM_BLOCK Lock value: " + str(lockvalue))
        while lockvalue[0] == 1:  # test just first byte of block to check if RSM_LOCKED
            logging.debug("Acquire: spinning...")
            lockvalue = self.RSM(RSM_BLOCK)
        # once the lock is acquired, check if need to invalidate cache
        self.CheckAndInvalidateCache()
        return 0

    def Release(self):
        logging.debug('Release')
        RSM_BLOCK = fsconfig.TOTAL_NUM_BLOCKS - 1
        # Put()s a zero-filled block to release lock
        self.Put(RSM_BLOCK,bytearray(fsconfig.RSM_UNLOCKED.ljust(fsconfig.BLOCK_SIZE, b'\x00')))
        return 0

    def CheckAndInvalidateCache(self):
        LAST_WRITER_BLOCK = fsconfig.TOTAL_NUM_BLOCKS - 2
        last_writer = self.Get(LAST_WRITER_BLOCK)
        # if ID of last writer is not self, invalidate and update
        if last_writer[0] != fsconfig.CID:
            if fsconfig.LOGCACHE == 1: print("CACHE_INVALIDATED")
            self.bcache = []
            for i in range(fsconfig.NUM_SERVERS):
                self.bcache.append({})
            updated_block = bytearray(fsconfig.BLOCK_SIZE)
            updated_block[0] = fsconfig.CID
            self.Put(LAST_WRITER_BLOCK,updated_block)

    ## Serializes and saves the DiskBlocks block[] data structure to a "dump" file on your disk

    def DumpToDisk(self, filename):

        logging.info("DiskBlocks::DumpToDisk: Dumping pickled blocks to file " + filename)
        file = open(filename,'wb')
        file_system_constants = "BS_" + str(fsconfig.BLOCK_SIZE) + "_NB_" + str(fsconfig.TOTAL_NUM_BLOCKS) + "_IS_" + str(fsconfig.INODE_SIZE) \
                            + "_MI_" + str(fsconfig.MAX_NUM_INODES) + "_MF_" + str(fsconfig.MAX_FILENAME) + "_IDS_" + str(fsconfig.INODE_NUMBER_DIRENTRY_SIZE)
        pickle.dump(file_system_constants, file)
        #pickle.dump(self.block, file)

        file.close()

    ## Loads DiskBlocks block[] data structure from a "dump" file on your disk

    def LoadFromDump(self, filename):

        logging.info("DiskBlocks::LoadFromDump: Reading blocks from pickled file " + filename)
        file = open(filename,'rb')
        file_system_constants = "BS_" + str(fsconfig.BLOCK_SIZE) + "_NB_" + str(fsconfig.TOTAL_NUM_BLOCKS) + "_IS_" + str(fsconfig.INODE_SIZE) \
                            + "_MI_" + str(fsconfig.MAX_NUM_INODES) + "_MF_" + str(fsconfig.MAX_FILENAME) + "_IDS_" + str(fsconfig.INODE_NUMBER_DIRENTRY_SIZE)

        try:
            read_file_system_constants = pickle.load(file)
            if file_system_constants != read_file_system_constants:
                print('DiskBlocks::LoadFromDump Error: File System constants of File :' + read_file_system_constants + ' do not match with current file system constants :' + file_system_constants)
                return -1
            block = pickle.load(file)
            for i in range(0, fsconfig.TOTAL_NUM_BLOCKS):
                self.Put(i,block[i])
            return 0
        except TypeError:
            print("DiskBlocks::LoadFromDump: Error: File not in proper format, encountered type error ")
            return -1
        except EOFError:
            print("DiskBlocks::LoadFromDump: Error: File not in proper format, encountered EOFError error ")
            return -1
        finally:
            file.close()


## Prints to screen block contents, from min to max

    def PrintBlocks(self,tag,min,max):
        print ('#### Raw disk blocks: ' + tag)
        for i in range(min,max):
            print ('Block [' + str(i) + '] : ' + str((self.Get(i)).hex()))
