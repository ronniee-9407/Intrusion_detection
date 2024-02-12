import minimalmodbus
import serial
import time


### connect the PLC
def connect_plc(com_port="COM3"):
    instrument = minimalmodbus.Instrument(com_port, 1, minimalmodbus.MODE_ASCII) #, debug = True) ## check com port in your system for me its "COM6"
    instrument.serial.port                                     # this is the serial port name
    instrument.serial.baudrate = 9600                          # Baudrate
    instrument.serial.bytesize = 7
    instrument.serial.parity   = serial.PARITY_EVEN
    instrument.serial.stopbits = serial.STOPBITS_ONE
    instrument.serial.timeout  = 2.0                           # seconds
    instrument.address                                         # this is the slave address number
    instrument.mode = minimalmodbus.MODE_ASCII                 # rtu or ascii mode
    instrument.clear_buffers_before_each_transaction = True
    # instrument.debug = True
    # print("parameter setting: ",instrument)
    print("PLC is connected to the system.")
    return instrument


def write_to_plc(plc_input):
    while True:
        instrument.write_bit(1281, plc_input)
        time.sleep(0.01)

if __name__ == "__main__":
    instrument = connect_plc()
    instrument.write_bit(1281, 0)

    # # # # instrument.serial.close()
    # while True:
    #     try:
    #         instrument.write_bit(1281, 0)
    #         # print(instrument.read_bit(1281))
    #         print("ok")

    #     except IOError:
    #         print(f"{time.time()}: Failed to read from instrument")
    #     time.sleep(0.001)
    