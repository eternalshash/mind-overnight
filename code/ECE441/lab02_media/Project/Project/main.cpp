#include <stdio.h>
#include <signal.h>
#include <sys/time.h>

#include "i2c-dev.h"
#include "ADXL345.h"

#define I2C_FILE_NAME "/dev/i2c-1" // for RPi B+
void INThandler(int sig);

int main(int argc, char **argv)
{
    // Open a connection to the I2C userspace control file.
    int i2c_fd = open(I2C_FILE_NAME, O_RDWR);
    if (i2c_fd < 0)
    {
        printf("Unable to open i2c control file, err=%d\n", i2c_fd);
        exit(1);
    }

    printf("Opened i2c control file, id=%d\n", i2c_fd);
    ADXL345 myAcc(i2c_fd);
    int ret = myAcc.init();
    if (ret)
    {
        printf("Failed init ADXL345, ret=%d\n", ret);
        exit(1);
    }

    usleep(100*1000);

    signal(SIGINT, INThandler);
    short ax, ay, az;

    // create file IO
    FILE *fp;
    fp = fopen("./output.txt", "w+");

    char TimeString[128];
    timeval curTime;

    while(1)
    {
        // get the current time
        gettimeofday(&curTime, NULL);
        strftime(TimeString, 80, "%Y-%m-%d %H:%M:%S",
                 localtime(&curTime.tv_sec));

        printf(TimeString);
        printf(":     ");

        // fetch data from ADXL345
        myAcc.readXYZ(ax, ay, az);

        // print to screen
        printf("Ax: %hi\t Ay: %hi\t Az: %hi\n", ax, ay, az);
        printf("----------------------\n");

        // print to file
        fprintf(fp, TimeString);
        fprintf(fp, ":     ");
        fprintf(fp, "Ax: %hi\t Ay: %hi\t Az: %hi\n", ax, ay, az);
        fprintf(fp, "----------------------\n");
    }

    fclose(fp);
    return 0;
}

void INThandler(int sig)
{
    signal(sig, SIG_IGN);
    exit(0);
}	
