"""
" @author: Justin Lathrop
"
" @param: Checks directory 'Orders' 
" for list of drinks to make. Steps 
" to make drink are included inside
" of drink order file in JSON format.
" If Admin folder contains any
" commands then they will be done
" first.
" Commnunicates to Arduino through
" Serial:
"   Responses:
"       - '0' => Error
"       - '1' => Success
"       - '2' => Unknown command
"       - '!' => Confirm/Emergency
"   Commands:
"       - 'L' => Dispense Liquid
"           <liquid number> <servings>
"       - 'T' => Move Tray
"           <number of spots to move>
"       - 'D' => Move down mixer
"       - 'U' => Move up mixer
"       - 'B' => Wait for start button
"       - 'P' => Parallel dispensing
"           <7 bytes -> array of servings>
"           <1 byte -> amount>
"       - 'R' => Reset tray
" When order is completed the drink
" item will be erased from 'Orders'
" directory and put into the 'Finished'
" directory, then controller will wait
" until arduino start button is pressed.
" 
" @return:
"   - errors => stdout
"   - other => stdout
"   - logging => logs.log (current dir)
"""
import thread
import threading
import serial
import time
import os
import json
import traceback
import sys
import operator

orderDir = './Orders'
completedDir = './OrdersCompleted'
adminDir = './Admin'
serialDevice = '/dev/ttyACM0'
baudRate = '115200'
drinks = {"Cherry": '0', "Orange": '1', "Grape": '2',
          "Lemonade": '3', "Strawberry": '4', "RaspberryLemonade": '5',
          "TropicalPunch": '6'}
drinkNames = ["Cherry", "Orange", "Grape", "Lemonade", "Strawberry",
              "RaspberryLemonade", "TropicalPunch"]
emergState = True
responseQueue = ''
semaphore = threading.BoundedSemaphore()
ser = serial.Serial(serialDevice, baudRate)#, timeout=0


def markOrderComplete():
    """
    " Marks current order as complete 
    " by removing it from the orderDir 
    " and appending it inside the 
    " completedDir.
    " 
    " @return: True if success and 
    " False if error.
    """
    orders = os.listdir(orderDir)
    if len(orders) > 0:
        # Save the current order
        orders.sort()
        orderName = orders[0]
        orderContents = json.load(open(orderDir + '/' + orders[0]))

	# Delete current order from order directory
        os.remove(orderDir + '/' + orderName)

	# Put current order into completed directory
        newFile = open(completedDir + '/' + str(time.time()) + '_' + orderName, 'w')
        newFile.write(json.dumps(orderContents))
        newFile.close()

        return True
    return False


def getNextOrder():
    """
    " Checks the 'Orders' directory
    " and gets the next order within
    " it.
    "
    " @return: order object if there is 
    " another order in the queue else 
    " return False.
    """
    orders = os.listdir(orderDir)
    if len(orders) > 0:
        orders.sort()
        return json.load(open(orderDir + '/' + orders[0]))
    else:
        return False


def listDone(List, val):
    """
    " Will check if all elements values in
    " the list are the same.
    "
    " @param: list, val
    "
    " @return: boolean
    """
    for x in List:
        if int(x['amount']) != val:
            return False
    return True


def smallestDrinkAmount(List):
    """
    " Given a list of drinks
    " find the smallest of the
    " amounts and return it.
    "
    " @param: List of drinks
    "
    " @return: int smallest amount
    """
    # 9 is the max amount for a drink
    # serving size
    amount = 9
    
    for d in List:
        if (int(d['amount']) < amount) and (int(d['amount']) > 0):
            amount = int(d['amount'])
    return amount


def updateDrinkAmounts(List, amount, index):
    """
    " Will subtract the smallest
    " amount from each item in
    " the list unless the item's
    " amount is already equal to
    " zero or less.
    "
    " @param: List of drinkItems, and
    "   int of amount to subtract.
    "
    " @return: Updated List
    """
    for i in List:
        if (int(i['amount']) > 0) and (drinkNames[index] == i['drink']):
            i['amount'] = str( int(i['amount']) - amount )
    return List


def getAmount(name, List):
    """
    " Finds the drink name in the List
    " and returns amount value.
    "
    " @param: string drink name,
    "   List of drinks
    "
    " @return: Int amount
    """
    for d in List:
        if d['drink'] == name:
            return int(d['amount'])
    return 0


def fillOrder(order):
    """
    " Fills the order of a drink and 
    " is in charge of sending commands 
    " to Arduino to process.
    " 
    " @param: Order <order> which holds 
    " all of the drinks information 
    " needed to create it. Serial
    " reference in order to commuincate
    " to the Arduino.
    " 
    " @return: True is successful and 
    " False if unsuccessful.
    """
    global emergState
    global responseQueue
    global ser
    print 'Filling order <' + order['title'] + '>'


    while not listDone(order['drinkList'], 0):
        semaphore.acquire()
        if emergState:
            semaphore.release()
            return False
        semaphore.release()
        count = 0
        msg = ''
        amount = smallestDrinkAmount(order['drinkList'])
        strDrinks = str(order['drinkList'])

        for index, d in enumerate(drinks):
            if count >= 3:
                msg = msg + '0'
            else:
                if (drinkNames[index] in strDrinks) and (getAmount(drinkNames[index], order['drinkList']) > 0):
                    msg = msg + '1'
                    count = count + 1
                    order['drinkList'] = updateDrinkAmounts(order['drinkList'], amount, index)
                else:
                    msg = msg + '0'

        msg = 'P' + msg + str(amount)
        semaphore.acquire()
        if emergState:
            semaphore.release()
            return False
        ser.write(msg)
        semaphore.release()
        
        print "Command Arduino to:"
        print "> Dispense Liquid in Parallel"
        print "> " + msg

        serIn = readSerial()
        semaphore.acquire()
        if emergState:
            semaphore.release()
            return False
        semaphore.release()
        print "Arduino Reponse:"
        print "> " + serIn
        print

    # Wait for liquid to clear tubes
    time.sleep(3)

    # Turn tray to next position
    semaphore.acquire()
    if emergState:
        semaphore.release()
        return False
    semaphore.release()
    print "Command Arduino to:"
    print "> Move tray 1 position"
    ser.write('T')
    ser.write('1')
    serIn = readSerial()
    semaphore.acquire()
    if emergState:
        semaphore.release()
        return False
    semaphore.release()
    print "Arduino Response:"
    print "> " + serIn
    print
    return True


def admin():
    """
    " Checks to see if there are any
    " admin commands to do.
    "
    " @return: True is folder is not
    " empty else False if it is.
    """
    commands = os.listdir(adminDir)
    if len(commands) > 0:
        return True
    else:
        return False


def fillAdminReq():
    """
    " Speaks to arduino for admin
    " simply printing out what
    " the arduino responds with
    " for testing purposes.
    """
    commands = os.listdir(adminDir)
        
    for el in commands:
        print 'Processing command ' + el
        if el == 'Turn_Tray.command':
            ser.write('T')
            ser.write('1')
            response = ser.read()
            print 'Arduino responded with ' + response
        elif el == 'Mix_Drink.command':
            ser.write('M')
            response = ser.read()
            print 'Arduino responded with ' + response
        elif el == 'Dispense_Drink_A.command':
            ser.write('A')
            response = ser.read()
            print 'Arduino responded with ' + response
        elif el == 'Dispense_Drink_B.command':
            ser.write('B')
            response = ser.read()
            print 'Arduino responded with ' + response
        else:
            print 'Command Unknown'

        os.remove(adminDir + '/' + el)


def readSerial():
    """
    " Reads from serial queue and
    " returns the next response from
    " the Arduino.  Should never be
    " the emergency response '!'.  If
    " no responses in the queue then
    " will busy wait until a response.
    "
    " @return: input char or False if
    " in emergency state.
    """
    global emergState
    global responseQueue
    
    semaphore.acquire()
    while not emergState:
        if len(responseQueue) > 0:
            return responseQueue[0]
        semaphore.release()
        time.sleep(0.2)
    semaphore.release()
    return False


def serialMonitor(name):
    """
    " Thread function for serial
    " monitoring.  Will watch
    " serial port and update the
    " serial queue when input from
    " the Arduino is made.
    """
    global emergState
    global responseQueue
    global ser
    
    time.sleep(2)
    semaphore.acquire()
    ser.flush()
    ser.flushInput()
    ser.flushOutput()
    semaphore.release()
    print "Serial Monitor Thread Initialized"

    semaphore.acquire()
    while ser.read() != '!':
        emergState = False
        semaphore.release()

    # Loop forever reading the serial port and
    # updating the responseQueue
    while True:
        semaphore.acquire()
        serIn = ser.read()
        semaphore.release()
        if serIn == '!':
            semaphore.acquire()
            emergState = True
            semaphore.release()
            print
            print "!!!! EMERGENCY BEGIN !!!!"
            print "Skipping current drink..."
            print "Will wait until Go button pressed..."
            semaphore.acquire()
            while ser.read() != '!':
                time.sleep(0.2)
            emergState = False
            responseQueue = ''
            semaphore.release()
            print "!!!! EMERGENCY FINISH !!!!"
            print
        else:
            semaphore.acquire()
            responseQueue = responseQueue + serIn
            semaphore.release()
        time.sleep(0.2)


def main():
    global emergState
    global responseQueue
    global ser
    
    try:
        print 'Initializing Controller'
        numDrinks = 0
        try:
            t = thread.start_new_thread(serialMonitor, ("SerialMonitor", ))
        except:
            print "Error initializing Serial Monitor Thread"

        # Wait until start button is pressed
        semaphore.acquire()
        while emergState:
            semaphore.release()
            time.sleep(0.2)
        semaphore.release()

        print 'Initialization Complete'
        print
        print "Command Arduino to:"
        print "> Reset Tray"
        ser.write('R')
        serIn = readSerial()
        print
        print "Arduino Response:"
        print "> " + serIn
        print

        # Loop forever filling orders
        while 1:
            semaphore.acquire()
            state = emergState
            semaphore.release()
            if not state:
                if admin():
                    fillAdminReq()
                else:
                    currentOrder = getNextOrder()
                    if currentOrder != False:
                        if fillOrder(currentOrder):
                            markOrderComplete()
                            numDrinks = numDrinks + 1
                            print '\n\nOrder complete\n\n'
                        else:
                            # Reset environment since Emergency happened
                            numDrinks = 0
                            markOrderComplete()
                            print "Failed to make order"
                            print "Reseting Environment"
                            print
                            print "Command Arduino to:"
                            print "> Reset Tray"
                            ser.write('R')
                            serIn = readSerial()
                            print
                            print "Arduino Response:"
                            print "> " + serIn
                            
                if numDrinks >= 6:
                    print "Six drinks have been made"
                    print "Command Arduino to:"
                    print "> Get start button press"
                    semaphore.acquire()
                    ser.write('B')
                    semaphore.release()
                    serIn = readSerial()
                    if serIn == '1':
                        print "Arduino Response:"
                        print "> " + serIn
                        numDrinks = 0
                        print "\nDrink count zeroed out\n"
                    else:
                        print "\n\nError getting user button press\n\n"
            time.sleep(2)
        print '\n\nController exited\n\n'
    except KeyboardInterrupt:
        print
        print 'Closing Serial Port'
        ser.close()
        print
        print 'Exiting...'
    except Exception:
        traceback.print_exc(file=sys.stdout)
    t.exit()
    sys.exit(0)



if __name__ == '__main__':
    main()
