import u6
import time
import select
import sys
import datetime
import numpy as np

# -----------------------------------------------------------------------------

def enterPressed():
	i,o,e = select.select([sys.stdin],[],[],0.0001)
	for s in i:
		if s == sys.stdin:
			input = sys.stdin.readline()
			return True
	return False

# -----------------------------------------------------------------------------
	
def decToBin(x, numDigits):
    val = int(bin(x)[2:])
    return ('%0' + str(numDigits) + 'd') % val

# -----------------------------------------------------------------------------

DAC0_REGISTER = 5000
# print(DAC0_REGISTER)
DAC1_REGISTER = 5002
bitDuration = 0.01 # [s]
chunkSeparator = 0.5 # [s]

# -----------------------------------------------------------------------------


lj = u6.U6()
lj.configU6()

while 1 == 1:
	
	now = datetime.datetime.now()
	y = now.year
	mo = now.month
	d = now.day
	h = now.hour
	mi = now.minute
	s = now.second
	ms = int(round(now.microsecond / 1000.0))
	# 48 bits information, plus one "1" at the start and at the end
	# makes 50 bits total
	arrNumBits = [12, 4, 5, 5, 6, 6, 10]
	arrData = [y, mo, d, h, mi, s, ms]
	sequence = '1' # always start with a one
	for i in range(len(arrData)):
		sequence += decToBin(arrData[i], arrNumBits[i])
	sequence += '1' # always end with a one
		
	print(arrData)
	print('\t', sequence)
	time0 = time.time()
	for i, c in enumerate(sequence):
		voltageLED = 0
		voltageREC = 0
		if c == '1':
                        voltageLED = 2.0
                        voltageREC = 1.0
		#print(i, c, voltage)
		#time1 = time.time()
		lj.writeRegister(DAC0_REGISTER, voltageLED)
		#time2 = time.time()
		#lj.writeRegister(DAC1_REGISTER, voltageREC)
		#time3 = time.time()
		#print(time2-time1,time3-time2,time3-time1)
		time.sleep(bitDuration)
	#timeend = time.time()
	#print(timeend-time0)
	lj.writeRegister(DAC0_REGISTER, 0) 
	#lj.writeRegister(DAC1_REGISTER, 0)
	time.sleep(chunkSeparator)
	
	if enterPressed():
		break
