# DisMass Client for Masscan
#
from twisted.conch.test.test_transport import factory
from __builtin__ import str

try:
    from OpenSSL import SSL
except:
    print 'You need openssl libs for python. apt-get install python-openssl'
    exit(-1)

import sys

try:
    from twisted.internet.protocol import ClientFactory, ReconnectingClientFactory
    from twisted.protocols.basic import LineReceiver
    from twisted.internet import ssl, reactor
except:
    print 'You need twisted libs for python. apt-get install python-twisted'
    exit(-1)
    

import time, getopt, shlex
from subprocess import Popen
from subprocess import PIPE
import os
import random

# Global variables
server_ip = False
server_port = 46002
vernum = '1.0'
# Your name alias defaults to anonymous
alias = 'Anonymous'
debug = False
# Do not use a max rate by default
maxrate = False
# End global variables 



# Print version information and exit
def version():
  print "+----------------------------------------------------------------------+"
  print "| DisMass_Client Version "+ vernum +"                                             |"
  print "| This program is free software; you can redistribute it and/or modify |"
  print "| it under the terms of the GNU General Public License as published by |"
  print "| the Free Software Foundation; either version 2 of the License, or    |"
  print "| (at your option) any later version.                                  |"
  print "|                                                                      |"
  print "| Author: RanShW.  Thanks for Garcia Sebastian(dnmap)                          |"
  print "| Start date : 2015-7-27                                                 |"
  print "+----------------------------------------------------------------------+"
  print


# Print help information and exit:
def usage():
  print "+----------------------------------------------------------------------+"
  print "| DisMass_Client Version "+ vernum +"                                             |"
  print "| This program is free software; you can redistribute it and/or modify |"
  print "| it under the terms of the GNU General Public License as published by |"
  print "| the Free Software Foundation; either version 2 of the License, or    |"
  print "| (at your option) any later version.                                  |"
  print "|                                                                      |"
  print "| Author: RanShW.  Thanks for Garcia Sebastian(dnmap)                          |"
  print "| Start date : 2015-7-27                                                  |"
  print "+----------------------------------------------------------------------+"
  print "\nusage: %s <options>" % sys.argv[0]
  print "options:"
  print "  -s, --server-ip        IP address of dismass server."
  print "  -p, --server-port      Port of dismass server. Dismass port defaults to 46001"
  print "  -a, --alias      Your name alias so we can give credit to you for your help. Optional"
  print "  -d, --debug      Debuging."
  print "  -m, --max-rate      Force masscans commands to use at most this rate. Useful to slow masscan down. Adds the --max-rate parameter."
  print
  sys.exit(1)
  
  


def check_clean(line):
    global debug
    try:
        outbound_chars = [';', '#', '`']
        ret = True
        for char in outbound_chars:
            if char in line:
                ret = False
        return ret

    except Exception as inst:
        print 'Problem in dataReceived function'
        print type(inst)
        print inst.args
        print inst





class MasscanClient(LineReceiver):
    def connectionMade(self):
        global client_id
        global alias
        global debug
        print 'Client connected successfully...'
        print 'Waiting for more commands....'
        
        if debug:
            print ' -- Your client ID is: {0} , and your alias is: {1}'.format(str(client_id), str(alias))
        
        euid = os.geteuid()
        
        # Do not send the euid, just tell if we are root or not.
        if euid == 0:
            # True
            iamroot = 1
        else:
            # False
            iamroot = 0
        
        # 'Client ID' text must be sent to receive another commands
        line = 'Starts the Client ID:{0}:Alias:{1}:Version:{2}:ImRoot:{3}'.format(str(client_id),str(alias),vernum,iamroot)
        if debug:
            print ' -- Line sent: {0}'.format(line)
        self.sendLine(line)
        
        line = 'Send more commands'
        if debug:
            print ' -- Line sent: {0}'.format(line)
        self.sendLine(line)    
    
    
    
    def dataReceived(self, line):
        global debug
        global client_id
        global alias
        
       
        # If a wait is received. just wait.
        if 'Wait' in line:
            sleeptime = int(line.split(':')[1])
            time.sleep(sleeptime)
            
            # Ask for more
            line = 'Send more commands'
            if debug:
                print ' -- Line sent: {0}'.format(line)
            self.sendLine(line)
        else:
            # DataReceived does not wait for end of lines or CR nor LF
            if debug:
                print "\tCommand Received: {0}".format(line.strip('\n').strip('\r'))
            
            # A little bit of protection from the server
            if check_clean(line):
                # Store the masscan output file so we can send it to the server later
                try:
                    masscan_output_file = line.split('-oX ')[1].split(' ')[0].strip(' ')
                except IndexError:
                    random_file_name = str(random.randrange(0, 100000000, 1)) + '.xml'
                    print '+ No -oX given. We add it anyway so not to lose the results. Added -oX '+random_file_name
                    line = line + '  -oX '+random_file_name
                    masscan_output_file = line.split('-oX ')[1].split(' ')[0].strip(' ')    
                    #print 'masscan output file' + masscan_output_file
                    
                try:
                    masscan_returncode = -1
                     
                    #Check for rate commands
                    #Verify that the server is NOT trying to force us to be faster.
                    if 'min-rate' in line:
                        temp_vect = shlex.split(line)
                        word_index = temp_vect.index('--min-rate')
                        # Just delete the --min-rate parameter with its value
                        masscan_command = temp_vect[0:word_index] + temp_vect[word_index + 1:]
                    else:
                        masscan_command = shlex.split(line) 
                    
                    # Do we have to add a max-rate parameter?
                    if maxrate:
                        masscan_command.append('--max-rate')
                        masscan_command.append(str((maxrate)))   
                        
                    # Strip the command, so we can control that only masscan is executed really
                    masscan_command = masscan_command[0:]
                    masscan_command.insert(0, 'masscan')
                    
                    # Recreate the final command to show it
                    masscan_command_string = ''
                    
                    for i in masscan_command:
                        masscan_command_string = masscan_command_string + i + ' '
                    
                    print "\tCommand Executed: {0}".format(masscan_command_string)
                    
                    masscan_process = Popen(masscan_command, stdout= PIPE)
                    raw_masscan_output = masscan_process.communicate()[0]
                    masscan_returncode = masscan_process.returncode
                    
                    
                        
                except OSError:
                    print 'You don\'t have masscan installed. You can install it with apt-get install masscan'
                    exit(-1)
    
                except ValueError:
                    raw_masscan_output = 'Invalid masscan arguments.'
                    print raw_masscan_output


                except Exception as inst:
                    print 'Problem in dataReceived function'
                    print type(inst)
                    print inst.args
                    print inst
                    
                
                
                if masscan_returncode >= 0:
                    # Masscan ended ok
                    
                    #Tell the server that we are sending the masscan output
                    print '\tSending output to the server...\n'
                    
                    line = 'Masscan Output File:{0}:'.format(masscan_output_file.strip('\n').strip('\r'))
                    if debug:
                        print ' -- Line sent: {0}'.format(line)
                    self.sendLine(line)
                    #self.sendLine(raw_masscan_output)
                    
                    masscan_file = open(random_file_name,'r')
                    # all_the_text = masscan_file.read( ) 
                    # self.sendLine(all_the_text)
                    for eachline in masscan_file:
                        self.sendLine(eachline)
                    
                    line = 'Masscan Output Finished:{0}:'.format(masscan_output_file.strip('\n').strip('\r'))
                    if debug:
                        print ' -- Line sent: {0}'.format(line)
                    self.sendLine(line)
                    
                    
                    # Move masscan output files to its directory
                    # 
                    # os.system('mv *.masscan masscan_output > /dev/null 2>&1')
                    # os.system('mv *.gmasscan masscan_output > /dev/null 2>&1')
                    # os.system('mv *.xml masscan_output > /dev/null 2>&1')
                    
                    # Ask for another command.
                    # 'Client ID' text must be sent to receive another command
                    print 'Waiting for more commands....'
                    #line = 'Send more commands to Client ID:{0}:Alias:{1}:'.format(str(client_id),str(alias))
                    line = 'Send more commands'
                    if debug:
                        print ' -- Line sent: {0}'.format(line)
                    self.sendLine(line)
            else:
                # Something strange was sent to us...
                print
                print 'WARNING! Ignoring some strange command was sent to us: {0}'.format(line)
                line = 'Send more commands'
                if debug:
                    print ' -- Line sent: {0}'.format(line)
                self.sendLine(line)
                
            os.system('mv *.xml masscan_output > /dev/null 2>&1')    
                
        

class MasscanClientFactory(ReconnectingClientFactory):
    try:
        protocol = MasscanClient
        
        def startedConnecting(self, connector):
            print 'Starting connection...'
            
        def clientConnectionFailed(self, connector, reason):
            print 'Connection failed:', reason.getErrorMessage()
            # Try to reconnect
            print 'Trying toe reconnect. Please wait...'
            ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        
        def clientConnectionLost(self, connector, reason):
            print 'Connection lost. Reason: {0}'.format(reason.getErrorMessage())
            # Try to reconnect
            print 'Trying to reconnect in 10 secs. Please wait...'
            ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
    except Exception as inst:
        print 'Problem in MasscanClientFactory'
        print type(inst)
        print inst.args
        print inst    
        
        
            
def process_commands():
    global server_ip
    global server_port
    global client_id
    global factory
    
    try:
        print 'Client Started...'
        
        # Generate the client unique ID
        client_id = str(random.randrange(0, 100000000, 1))
        
        # Create the output directory
        print 'Masscan output files stored in \'masscan_output\' directory...'
        os.system('mkdir masscan_output > /dev/null 2>&1')
        
        factory = MasscanClientFactory()
        # Do not wait more that 10 seconds between reconnections
        factory.maxDelay = 10
        reactor.connectSSL(str(server_ip), int(server_port), factory, ssl.ClientContextFactory())
        reactor.run()
    except Exception as inst:
        print 'Problem in process_commands function'
        print type(inst)
        print inst.args
        print inst 
    
    
    
    
def main():
    global server_ip
    global server_port
    global alias
    global debug
    global maxrate
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "a:dm:p:s:", ["server-ip=","server-port","max-rate","alias=","debug"])
    except getopt.GetoptError: usage()
    
    for opt, arg in opts:
        if opt in ("-s", "--server-ip"): server_ip=str(arg)
        if opt in ("-p", "--server-port"): server_port=arg
        if opt in ("-a", "--alias"): alias=str(arg).strip('\n').strip('\r').strip(' ')
        if opt in ("-d", "--debug"): debug=True
        if opt in ("-m", "--max-rate"): maxrate=str(arg)
        
    try:
        if server_ip and server_port:
            version()
            
            # Start connecting
            process_commands()
            
        else:
            usage()
            
    except KeyboardInterrupt:
        # CTRL-C pretty handling.
        print 'Keyboard Interruption!. Exiting.'
        sys.exit(1)   
        
        
if __name__ == '__main__':
    main() 
        
        
          