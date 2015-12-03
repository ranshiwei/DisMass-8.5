# DisMass Server for Masscan
# 
import logging
import logging.handlers
import datetime
try:
    from twisted.internet.protocol import Factory, Protocol
    from twisted.internet import reactor
    from twisted.internet import task
    from twisted.python import log
    from twisted.python.logfile import DailyLogFile
except:
    print 'You need twisted library. apt-get install python-twisted-bin python-twisted-core'
    exit(-1)

import getopt, sys, time, os
try:
    from OpenSSL import SSL
except:
    print 'You need python openssl library. apt-get install python-openssl'
    exit(-1)
    
    
    
# Global Variables

vernum = '1.0'
masscan_commands_file = ''
masscan_command = []
masscan_commands_sent = []
file_descripter = ''
trace_file = ''
masscan_output_coming_back = False
output_file_descriptor = ''
file_position = 0
clients = {}
port = 46002
log_file = '/var/log/dismass_server.log'
log_level = 'info'
clientes = {}
verbose_level = 2

# This is to assure that the first time we run, something is shown
temp = datetime.datetime.now()
delta = datetime.timedelta(seconds=5)
last_show_time = temp - delta

#defaults to 1 hour
client_timeout = 3600

sort_type = 'Status'

#By default in the same directory
pemfile = 'server.pem'

#End of global variables

# Print version information and exit
def version():
  print "+----------------------------------------------------------------------+"
  print "| DisMass_server Version "+ vernum +"                                           |"
  print "|                                                                      |"
  print "| Author: RanShW.  Thanks for Garcia Sebastian(dnmap)                  |"
  print "| Start date : 2015-7-25                                               |"
  print "+----------------------------------------------------------------------+"
  print
  
# Print help information and exit:  
def usage():
  print "+----------------------------------------------------------------------+"
  print "| DisMass_server Version "+ vernum +"                                  |"
  print "|                                                                      |"
  print "| Author: RanShW   Thanks for Garcia Sebastian(dnmap)                  |"
  print "| Start date : 2015-7-25                                               |"
  print "+----------------------------------------------------------------------+"
  print "\nusage: %s <options>" % sys.argv[0]
  print "options:"
  print "  -f, --masscan-commands        masscan commands file"
  print "  -p, --port        TCP port where we listen for connections."
  print "  -L, --log-file        Log file. Defaults to /var/log/dismass_server.conf."
  print "  -l, --log-level       Log level. Defaults to info."
  print "  -v, --verbose_level         Verbose level. Give a number between 1 and 5. Defaults to 1. Level 0 means be quiet."
  print "  -t, --client-timeout         How many time should we wait before marking a client Offline. We still remember its values just in case it cames back."
  print "  -s, --sort             Field to sort the statical value. You can choose from: Alias, #Commands, UpTime, RunCmdXMin, AvrCmdXMin, Status"
  print "  -P, --pem-file         pem file to use for TLS connection. By default we use the server.pem file provided with the server in the current directory."
  print
  print "dismass_server uses a \'<masscan-commands-file-name>.dismasstrace\' file to know where it must continue reading the masscan commands file. If you want to start over again,"
  print "just delete the \'<masscan-commands-file-name>.dismasstrace\' file"
  print
  sys.exit(1)



def timeout_idle_clients():
    """
    This function search for idle clients and mark them as offline, so we do not display them
    """
    global mlog
    global verbose_level
    global clients
    global client_timeout
    try:
        for client_id in clients:
            now = datetime.datetime.now()
            time_diff = now - clients[client_id]['LastTime']
            if time_diff.seconds >= client_timeout:
                clients[client_id]['Status'] = 'Offline'
    
    except Exception as inst:
        if verbose_level > 2:
            msgline = 'Problem in mark_as_idle function'
            mlog.error(msgline)
            print msgline
            msgline = type(inst)
            mlog.error(msgline)
            print msgline
            msgline = inst.args
            mlog.error(msgline)
            print msgline
            msgline = inst
            mlog.error(msgline)
            print msgline            




def read_file_and_fill_masscan_variable():  
    """ Here we fill the masscan_command with the lines of the txt file. Only the first time. Later this file should be filled automatically"""
    global masscan_commands_file
    global masscan_command
    global file_descripter
    global trace_file
    global file_position
    global mlog
    global verbose_level
    
    if not file_descripter:
        file_descripter = open(masscan_commands_file, 'r')
    
    last_line = ''
    #if not trace_file_descriptor:
    trace_file = masscan_commands_file + '.dismasstrace'
    
    try:
        size = os.stat(trace_file).st_size
        trace_file_descriptor = open(trace_file, 'r')
        if size > 0:
            # We already have a trace file. We must be reading the same original file again after some running...
            trace_file_descriptor.seek(0)
            last_line = trace_file_descriptor.readline()
            
            # Search for the line stored in the trace file
            # This allow us to CTRL-C the server and reload it again without having to worry about where we reading commands...
            otherline = file_descripter.readline()
            while otherline:
                if last_line == otherline:
                    break
                otherline = file_descripter.readline()
        trace_file_descriptor.close()
        
    except OSError:
        pass
    
    # Do we have some more lines added since last time?
    if file_position != 0:
        # If we are called again, and the file was already read. Close the file so we can 'see' the new commands added
        # and then continue from the last previous line...
        file_descripter.flush()
        file_descripter.close()
        file_descripter = open(masscan_commands_file, 'r')
        
        # Go forward until what we read last time
        file_descripter.seek(file_position)
        
    line = file_descripter.readline()
    file_position = file_descripter.tell()
    lines_read = 0
    while line:
        # Avoid lines with # so we can comment on them
        if not '#' in line:
            masscan_command.insert(0, line)
        line = file_descripter.readline()
        file_position = file_descripter.tell()
        lines_read += 1
        
    
    msgline = 'Command lines read: {0}'.format(lines_read)
    mlog.debug(msgline)




class ServerContextFactory:
    global mlog
    global verbose_level
    global pemfile
    # Copyright (c) Twisted Matrix Laboratories.
    """ Only to set up SSL"""
    def getContext(self):
        """
        Create an SSL context.
        This is a sample implementation that loads a certificate from a file 
        called 'server.pem'.
        The file server.pem was copied from apache!
        """
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        try:
            ctx.use_certificate_file(pemfile)
            ctx.use_privatekey_file(pemfile)
        except:
            print 'You need to have a server.pem file for the server to work. If it is not in your same directory, just point to it with -P parameter'
        return ctx
    
    
    
    
def show_info():
    global verbose_level
    global mlog
    global clients
    global last_show_time
    global start_time
    global sort_type
    
    try:
        now = datetime.datetime.now()
        diff_time = now - start_time
        
        amount = 0
        for j in clients:
            if clients[j]['Status'] != 'Offline':
                amount += 1
        
        if verbose_level > 0:
            line = '=| MET:{0} | Amount of Online clients: {1} |='.format(diff_time, amount)
            print line
            mlog.info(line)
            
        if clients != {}:
            if verbose_level > 1:
                line = 'Clients connected'
                print line
                mlog.info(line)
                line = '------------------'
                print line
                mlog.info(line)
                #line = '{0:15}\t{1}\t{2}\t{3}\t{4}\t\t{5}\t{6}\t{7}\t{8}\t{9}'.format('Alias','#Commands','Last Time Seen', '(time ago)', 'UpTime', 'Version', 'IsRoot', 'RunCmdXMin', 'AvrCmdXMin', 'Status')
                line = '{0:15}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}'.format('Alias','#Commands','Last Time Seen', '(time ago)', 'RunCmdXMin', 'AvrCmdXMin', 'Status')
                print line
                mlog.info(line)
                for i in clients:
                    if clients[i]['Status'] != 'Offline':
                        temp = clients[i]['LastTime'].ctime().split(' ')[1:-1]
                        lasttime = ''
                        for j in temp:
                            lasttime = lasttime +str(j) + ' '
                        time_diff = datetime.datetime.now() - clients[i]['LastTime']
                        time_diff_secs = int((time_diff.seconds + (time_diff.microseconds / 1000000.0) ) % 60)
                        
                        time_diff_mins = int(  (time_diff.seconds + (time_diff.microseconds / 1000000.0) ) / 60)
                        
                        #uptime_diff = datetime.datetime.now() - clients[i]['FirstTime']
                        
                        #uptime_diff_hours = int( (uptime_diff.seconds + (uptime_diff.microseconds / 1000000.0)) / 3600)
                        
                        #uptime_diff_mins = int( ((uptime_diff.seconds % 3600) + (uptime_diff.microseconds / 1000000.0)) / 60)
                        
                        #line = '{0:15}\t{1}\t\t{2}({3:2d}\'{4:2d}\")\t{5:2d}h{6:2d}m\t\t{7}\t{8}\t{9:10.1f}\t{10:9.1f}\t{11}'.format(clients[i]['Alias'], clients[i]['NbrCommands'], lasttime, time_diff_mins, time_diff_secs, uptime_diff_hours, uptime_diff_mins , clients[i]['Version'], clients[i]['IsRoot'], clients[i]['RunCmdsxMin'], clients[i]['AvrCmdsxMin'], clients[i]['Status'])
                        line = '{0:15}\t{1}\t\t{2}({3:2d}\'{4:2d}\")\t{5:10.1f}\t{6:9.1f}\t{7}'.format(clients[i]['Alias'], clients[i]['NbrCommands'], lasttime, time_diff_mins, time_diff_secs, clients[i]['RunCmdsxMin'], clients[i]['AvrCmdsxMin'], clients[i]['Status'])
                        print line
                        mlog.info(line)
                        
            print
            last_show_time = datetime.datetime.now()
            
    except Exception as inst:
        if verbose_level > 2:
            msgline = 'Problem in show_info function'
            mlog.error(msgline)
            print msgline
            msgline = type(inst)
            mlog.error(msgline)
            print msgline
            msgline = inst.args
            mlog.error(msgline)
            print msgline
            msgline = inst
            mlog.error(msgline)
            print msgline                        
    
    
    
    
def send_one_more_command(ourtransport, client_id):
    # Extract the next command to send.
    global masscan_command
    global verbose_level
    global mlog
    global clients
    
    try:
        alias = clients[client_id]['Alias']
        
        command_to_send = masscan_command.pop()
        
        line = 'Data sent to client ID '+ client_id + ' ('+alias+')'
        log.msg(line, LogLevel = logging.INFO)
        if verbose_level > 2:
            print line
        line = '\t' + command_to_send.strip('\n')
        log.msg(line, LogLevel = logging.INFO)
        if verbose_level > 2:
            print line
        ourtransport.transport.write(command_to_send)
        clients[client_id]['NbrCommands'] += 1
        clients[client_id]['LastCommand'] = command_to_send
        clients[client_id]['Status'] = 'Executing'
        
    except IndexError:
        # If the list of commands is empty, look for new commands
        line = 'No more commands in queue.'
        log.msg(line, LogLevel = logging.DEBUG)
        if verbose_level > 2:
            print line
        line = '\tMaking the client ' + str(client_id)+' ('+str(alias)+')'+' wait 10 secs for new commands to arrive...'
        log.msg(line, LogLevel = logging.DEBUG)
        if verbose_level > 2:
            print line
        clients[client_id]['Status'] = 'Executed'
        ourtransport.transport.write('Wait:10')
    except Exception as inst:
        print 'Problem in Send More COmmands'
        print type(inst)
        print inst.args
        print inst
        



def process_input_line(data, ourtransport, client_id):
    global mlog
    global verbose_level
    global clients
    global trace_file
    global masscan_command
    global masscan_output_coming_back
    global output_file_descriptor
    
    try:
        # What to do. Send another command or store the masscan output?
        if 'Starts the Client ID:' in data:
            # No more masscan lines coming back
            if masscan_output_coming_back:
                masscan_output_coming_back = False
                
            alias = data.split(':')[3].strip('\n').strip('\r').strip(' ')
            try:
                client_version = data.split(':')[5].strip('\n').strip('\r').strip(' ')
                client_isroot = 'False' if data.split(':')[7].strip('\n').strip('\r').strip(' ') ==0 else 'True'
            except:
                # It is an old version and it is not sending these data
                client_version = '1.0?'
                client_isroot = '?'
                
            try:
                # Do we have it yet?
                value = clients[client_id]['Alias']
                # Yes
            except KeyError:
                # No
                clients[client_id] = {}
                clients[client_id]['Alias'] = alias
                clients[client_id]['FirstTime'] = datetime.datetime.now()
                clients[client_id]['LastTime'] = datetime.datetime.now()
                clients[client_id]['NbrCommands'] = 0
                clients[client_id]['Status'] = 'Online'
                clients[client_id]['LastCommand'] = ''
                clients[client_id]['Version'] = client_version
                clients[client_id]['IsRoot'] = client_isroot
                clients[client_id]['RunCmdsxMin'] = 0
                clients[client_id]['AvrCmdsxMin'] = 0
                
            msgline = 'Client ID connected: {0} ({1})'.format(str(client_id), str(alias))
            log.msg(msgline, LogLevel = logging.INFO)
            if verbose_level > 1:
                print '+ ' + msgline
                
        elif 'Send more commands' in data:
            alias = clients[client_id]['Alias']
            
            clients[client_id]['Status'] = 'Online'
            nowtime = datetime.datetime.now()
            clients[client_id]['LastTime'] = nowtime
            
            # No more masscan lines coming back
            if masscan_output_coming_back:
                masscan_output_coming_back = False
                
            send_one_more_command(ourtransport, client_id)
        
        
        elif 'Masscan Output File' in data and not masscan_output_coming_back:
            # Masscan output start to come back...
            masscan_output_coming_back = True
            
            alias = clients[client_id]['Alias']
            clients[client_id]['Status'] = 'Online'
             
            # Compute the commands per hour
            time_since_cmd_start = datetime.datetime.now() - clients[client_id]['LastTime']
            
            prev_ca = clients[client_id]['AvrCmdsxMin']
            
            clients[client_id]['RunCmdsxMin'] =  60 / ( time_since_cmd_start.seconds + ( time_since_cmd_start.microseconds / 1000000.0))
            clients[client_id]['AvrCmdsxMin'] = ( clients[client_id]['RunCmdsxMin'] + (clients[client_id]['NbrCommands'] * prev_ca) ) / ( clients[client_id]['NbrCommands'] + 1 )
            
            # update the lasttime
            nowtime = datetime.datetime.now()
            clients[client_id]['LastTime'] = nowtime
            
            # Create the dir
            os.system('mkdir masscan_results > /dev/null 2>&1')
             
            # Get the output file from the data
            # We strip \n
            masscan_output_file = 'masscan_results/'+ data.split(':')[1].strip('\n')
            if verbose_level > 2:
                log.msg('\tMasscan output file is: {0}'.format(masscan_output_file), LogLevel = logging.DEBUG)
            
            output_file_descriptor = open(masscan_output_file, 'a+')
            
            output_file_descriptor.writelines('Client ID:'+client_id+':Alias:'+ alias)
            output_file_descriptor.flush()    
        
        elif masscan_output_coming_back and 'Masscan Output Finished' not in data:
            #Store the output to a file
            
            alias = clients[client_id]['Alias']
                        
            clients[client_id]['status'] = 'Storing'
            nowtime = datetime.datetime.now()
            clients[client_id]['LastTime'] = nowtime
            
            log.msg('\tStoring masscan output for client {0} ({1}).'.format(client_id, alias), LogLevel = logging.DEBUG)
            output_file_descriptor.writelines(data + '\n')
            output_file_descriptor.flush()
            
        
        elif 'Masscan Output Finished' in data and masscan_output_coming_back:
            # Masscan output finished 
            masscan_output_coming_back = False
            
            alias = clients[client_id]['Alias']
            
            clients[client_id]['Status'] = 'Online'
            nowtime = datetime.datetime.now()
            clients[client_id]['LastTime'] = nowtime
            
            #Store the finished masscan command in the file, so we can retrieve it if we need...
            finished_masscan_command = clients[client_id]['LastCommand']
            trace_file_descriptor = open(trace_file, 'w')
            trace_file_descriptor.seek(0)
            trace_file_descriptor.writelines(finished_masscan_command)
            trace_file_descriptor.flush()
            trace_file_descriptor.close()
            
            if verbose_level > 2:
                print '+ Storing command {0} in trace file.'.format(finished_masscan_command.strip('\n').strip('\r'))
            
            output_file_descriptor.close()
            
    except Exception as inst:
        print 'Problem in process input lines'
        print type(inst)
        print inst.args
        print inst
  
       


class MasscanServerProtocol(Protocol):
    """ This is the function that communicates with the client """
    global mlog
    global verbose_level
    global clients
    global masscan_command
    global mlog
    
    def connectionMade(self):
        if verbose_level > 0:
            pass
    
    def connectionLost(self, reason):
        peerHost = self.transport.getPeer().host
        peerPort = str(self.transport.getPeer().port)
        client_id = peerHost + ':' + peerPort
        alias = clients[client_id]['Alias']
        
        if verbose_level > 1:
            msgline = 'Connection lost in the protocol. Reason:{0}'.format(reason)
            msgline2 = '+ Connection lost for {0} ({1}).'.format(alias,client_id)
            log.msg(msgline, LogLevel = logging.DEBUG)
            print msgline2
            # Offline redo the last command
            clients[client_id]['Status'] = 'Offline'
            command_to_redo = clients[client_id]['LastCommand']
            if command_to_redo != '':
                masscan_command.append(command_to_redo)
            if verbose_level > 2:
                print 'Re inserting command: {0}'.format(command_to_redo)
                
    def dataReceived(self, newdata):
        #global client_id
        
        data = newdata.strip('\r').strip('\n').split('\r\n')
        
        peerHost = self.transport.getPeer().host
        peerPort = str(self.transport.getPeer().port)
        client_id = peerHost + ':' + peerPort
        
        # If you need to debug
        if verbose_level > 2:
            log.msg('Data received', LogLevel = logging.DEBUG)
            log.msg(data, LogLevel = logging.DEBUG)
            print '+ Data received: {0}'.format(data)
            
        for line in data:
            process_input_line(line,self,client_id)
            
                
    
    
    
def process_masscan_commands(logger_name):
    """ Main function. Here we set up the environment, factory and port """
    global masscan_commands_file
    global masscan_command
    global port
    global mlog
    global verbose_level
    global client_timeout

    observer = log.PythonLoggingObserver(logger_name)
    observer.start()
    
    # Create the factory
    factory = Factory()
    factory.protocol = MasscanServerProtocol
    
    # Create the time based print
    loop = task.LoopingCall(show_info)
    loop.start(5.0) 
    
    # Create the time based file read
    loop2 = task.LoopingCall(read_file_and_fill_masscan_variable)
    loop2.start(30.0) 
    
    # To mark idel clients as hold
    loop3 = task.LoopingCall(timeout_idle_clients)
    loop3.start(client_timeout) 
    
    # Create the reactor
    reactor.listenSSL(port, factory, ServerContextFactory())
    reactor.run()
    



def main():
    global masscan_commands_file
    global port
    global log_file
    global log_level
    global mlog
    global verbose_level
    global start_time
    global client_timeout
    global sort_type
    global pemfile
    
    start_time = datetime.datetime.now()
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:l:L:p:P:s:t:v:", ["masscan-commands=","log-level=","log-server=","port=","pem-file=", "sort-type=","client-timeout=","verbose-level="])
    except getopt.GetoptError: usage()
    
    for opt, arg in opts:
        if opt in ("-f", "--masscan-commands"): masscan_commands_file = str(arg)
        if opt in ("-p", "--port"): port = int(arg)
        if opt in ("-l", "--log-level"): log_level = arg
        if opt in ("-L", "--log-file"): log_file = arg
        if opt in ("-v", "--verbose-level"): verbose_level = int(arg)
        if opt in ("-t", "--client-timeout"): client_timeout = int(arg)
        if opt in ("-s", "--sort-type"): sort_type = str(arg)
        if opt in ("-P", "--pem-file"): pemfile = str(arg)    
    
    try:
        #Verify that we have a pem file
        try:
            temp = os.stat(pemfile)
        except OSError:
            print 'No pom file given. Use -P'
            exit(-1)
        
        if masscan_commands_file != '':
            if verbose_level > 0:
                version()
            
            # Set up logger
            # Set up a specific logger with our desired output level
            logger_name = 'MyLogger'
            mlog = logging.getLogger(logger_name)
            
            # Set up the log level
            numeric_level = getattr(logging, log_level.upper(), None)
            if not isinstance(numeric_level, int):
                raise ValueError('Invalid log level: %s' % log_level) 
            mlog.setLevel(numeric_level)
            
            # Add the log message handler to the logger
            handler = logging.handlers.RotatingFileHandler(log_file,backupCount = 5)
            
            formater = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formater)
            mlog.addHandler(handler)
            # End logger
            
            # First fill the variable from the file
            read_file_and_fill_masscan_variable()
            
            # Start processing clients
            process_masscan_commands(logger_name)
            
        else:
            usage()
        
    except KeyboardInterrupt:
        # CTRL-C pretty handling.
        print 'Keyboard Interruption!. Exiting.'
        sys.exit(1)

    
if __name__ == '__main__':
    main()
        



















