#!/usr/bin/python
from netmiko import ConnectHandler
import yaml,logging,logging.config,sys,time
from nornir.core import InitNornir
from nornir.plugins.tasks.networking import netmiko_send_command
from nornir.plugins.functions.text import print_result
import time

def findNei(x,iface):
  '''
  search neighbor in list matching provided local_interface
  '''
  return next(i for i in x if i['local_interface'] == iface)

def readExpected(dataFile):
  '''
  read expected topology from previously saved file
  '''
  logger.info("OPENING FILE WITH CORRECT DATA")
  try:
    with open(dataFile, 'r') as data:
      expected = yaml.load(data)
      data.close()
  except:
    logger.error("MISSING OR UNREADABLE DATAFILE %s" , dataFile)
    return 0
  return expected

def compareTopology(current,expected,nr):
  '''
  compare current and expected tpology
  show matches and differences
  '''
  ifaceCounter=0 # count number of interfaces compared
  for device in expected:

    # if device is found in current
    if current.get(device):
      for expected_neighbor in expected.get(device):
        current_neighbor=0
        # if iface is not in exclusion list named excludeIface in groups.yaml
        if not [el for el in nr.inventory.hosts.get(device).get('excludeIface') if expected_neighbor.get('local_interface') in el]:
          try:
            current_neighbor=findNei(current.get(device),expected_neighbor.get('local_interface'))
          except:
            # if neighbor is not found
            print("%s MISSING NEIGHBOR - EXPECTED %s ON LOCAL INTERFACE %s REMOTE INTERFACE %s" % (device, expected_neighbor.get('neighbor'), expected_neighbor.get('local_interface'),expected_neighbor.get('neighbor_interface')))
          # if neighbor is found check capabilities are not in excludeCapa in groups.yaml
          if current_neighbor and not [el for el in nr.inventory.hosts.get(device).get('excludeCapa') if el in expected_neighbor.get('capability')]:
            #reset timers to allow to compare
            ifaceCounter+=1
            expected_neighbor['holdtime']=0
            current_neighbor['holdtime']=0
            if expected_neighbor == current_neighbor:
              print("%s EXPECTED NEIGHBOR %s FOUND ON LOCAL INTERFACE %s REMOTE INTERFACE %s" % (device,expected_neighbor.get('neighbor'), expected_neighbor.get('local_interface'),expected_neighbor.get('neighbor_interface')))
            else:
              print("%s CHANGED NEIGHBOR - EXPECTED %s ON LOCAL INTERFACE %s REMOTE INTERFACE %s BUT FOUND %s ON REMOTE PORT %s" % (device,expected_neighbor.get('neighbor'), expected_neighbor.get('local_interface'),expected_neighbor.get('neighbor_interface'),current_neighbor.get('neighbor'),current_neighbor.get('neighbor_interface')))
    else:
      print ("***** %s MISSING OR INACESSIBLE DEVICE *****" % device)
  logger.info("TOTAL INTERFACES COMPARED %s" % ifaceCounter)

def main():

  dataFile = 'expected-NOR.yml'   # expected results or new file to write results
  currentFile = 'current-NOR.yml' # current read
  nr = InitNornir(logging_loggers=['nornir','__main__'])
 
  command = 'show cdp neighbors'
  logger.info("RUNNING COMMAND %s" % command) 
  start = time.time()
  result = nr.run(task=netmiko_send_command,command_string=command,use_textfsm=True)
  end = time.time()
  logger.info("COMMANDS RUN IN %s" , str(round(end-start,1)))

  # convert nornir output to dictionary
  current = {}
  for key in result:
    current[key]= result[key][0].result

  expected = readExpected(dataFile)    
  if not expected: # if dataFile is missing write current read to dataFile
    with open(dataFile, 'w') as dF:
      yaml.dump(current, dF, default_flow_style=False)
    dF.close()
    logger.info("EXISTING DATA MISSING - WRITTEN CURRENT TO FILE %s" % dataFile)
    print("EXISTING DATA MISSING - WRITTEN CURRENT TO FILE %s" % dataFile)
  else: # if a dataFile is present proceed with compare
    with open(currentFile, 'w') as dF:
      yaml.dump(current, dF, default_flow_style=False)
    dF.close()
    logger.info("WRITTEN CURRENT TO FILE %s" % currentFile)
    compareTopology(current,expected,nr)

  end = time.time()
  logger.info("TOTAL RUNTIME %s" , str(round(end-start,1)))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
main()