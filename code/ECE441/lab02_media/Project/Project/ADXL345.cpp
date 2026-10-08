/*
Basic readout of ADXL345 accelerometer via I2C 

Oryginal code taken from the very bottom of this page:
http://www.raspberrypi.org/forums/viewtopic.php?t=55834

Updated by Jan Balewski, August 2014
Further updated by Mikhail Gromov, June 2025 - Added debug logging
*/

#include <assert.h>
#include "ADXL345.h"

//==========================================
//==========================================
bool ADXL345::selectDevice(){
   if (ioctl(fd, I2C_SLAVE, myAddr) < 0) {
      fprintf(stderr, "device ADXL345 not present\n");
      return false;
   }
   return true;
}

//==========================================
//==========================================
bool ADXL345::writeToDevice(char *buf, int len) {
    int ret = write(fd, buf, len);
    if (ret != len) {
        fprintf(stderr,
                "ADXL345 write failed: wrote %d of %d bytes. errno=%d (%s)\n",
                ret, len, errno, strerror(errno));
        return false;
    }
    return true;
}



//===============
bool  ADXL345::readXYZ( short &x , short &y, short &z) {
  assert(fd>0); // crash if port was not opened earlier
  if(!selectDevice())   return false;
  //   printf("selectDevice(fd,ADXL345...)  passed\n");
  char buf[7];
  buf[0] = 0x32;     // This is the register we wish to read from
  if(!writeToDevice(buf,2))     return false;
   
  if (read(fd, buf, 6) != 6) {  // Read back data into buf[]
    printf("Unable to read from slave for ADXL345\n");
    return false;
  }  else {
    x = (buf[1]<<8) |  buf[0]; 
    y = (buf[3]<<8) |  buf[2];
    z = (buf[5]<<8) |  buf[4];
  }
  return true;
} 


//==========================================
//==========================================
//==========================================
int ADXL345::init()  {  
  assert(fd>0); // crash if port was not opened earlier
  char buf[6];       // Buffer for data being read/ written on the i2c bus
  
  if(!selectDevice()) return -1;
  
  buf[0] = 0x2d;                   // Commands for performing a ranging
  buf[1] = 0x18;
  
  if(!writeToDevice(buf,2))  return -2;
  
   buf[0] = 0x31;              // Commands for performing a ranging
   buf[1] = 0x0A; //09 4g , A 8g
   
   if(!writeToDevice(buf,2))  return -3;
   printf("ADXL345::init() OK\n");
   return 0; 
}
