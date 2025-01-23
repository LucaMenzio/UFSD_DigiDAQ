GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

#echo -e "${CYAN}installing CAEN Digitizer packages${NC}"
#CAENComm
#cd /home/daq/Desktop/DigiDAQ/Drivers/Digitizer/from_ws_lab/CAENComm-v1.6.0/lib
#sudo ./install_x64
#CAENDigitizer
#cd /home/daq/Desktop/DigiDAQ/Drivers/Digitizer/from_ws_lab/CAENDigitizer-v2.17.3/lib
#sudo ./install_x64
#CAENVMELib
#cd /home/daq/Desktop/DigiDAQ/Drivers/Digitizer/from_ws_lab/CAENVMELib-v3.4.1/lib
#sudo ./install_x64
#CAEN USB
cd /home/tb_pc/Downloads/CAENUSBdrvB-1.5.4/
sudo make && sudo make install -j10
#CONET connection (fiber)
#cd /home/daq/Drivers/Digitizer/A4818_driver/
#sudo sh reg_A4818.sh
echo -e "${GREEN}finished with the setup of CAEN dependancies${NC}"
echo "Going back to UFSDPyDAQ folder"
cd /home/tb_pc/Desktop/DigiDAQ/UFSDPyDAQ_VME_32ch
