# UFSDPyDAQ
#instructions for FindLinkNum

# In case the digitizer cannot be found even when connected, it is possible that its LinkNum was changed by the system.
# "Keep an eye on the LinkNum. They like to change."
# If that happens run 

./FindDigitizer.bin

# which, if successful, returns the current correct value of LinkNum.
# (the executable source is /home/daq/Desktop/DigiDAQ/Drivers/Digitizer/CAENDigitizer-2.16.3/samples/ReadoutTest_Digitizer/src/ReadoutTest_Digitizer.c )
# Note down its value and insert it in the config file (WaveDumpConfig_X742.txt at the moment).
# Open it and you will find OPEN USB *insert_LinkNum_here* 0
# Example: OPEN USB 2 0
# Save the config file and re-run

wavedump WaveDumpConfig_X742.txt

# roberto.mulargia@cern.ch
# UFSD_DigiDAQ
