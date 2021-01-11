#include <IRremote.h>
#include <IRremoteInt.h>
#include <Wire.h>

//Software config
#define I2C_SLAVE_DEFAULT_ADDR 0x05

//Hardware config
const byte reg_size = 33;
const byte reg_size2 = 64;
volatile uint16_t i2c_regs[reg_size];
volatile uint16_t rawCodes[reg_size2];
byte LastMasterCommand = 0;

/*
 * Internal variables
 */
volatile byte reg_position;
IRsend irsend3;    //pin 3
IRsend2 irsend9;  //pin 9

void setup() 
{
  //Start I2C
  Wire.begin(I2C_SLAVE_DEFAULT_ADDR);
  Wire.onReceive(i2cReceiveEvent);
  Wire.onRequest(i2cRequestEvent);
  //start serial
  Serial.begin(115200);
  Serial.println("I2C READY!");
}

//sw reset function
void(*resetFunc)(void)=0;

void loop() 
{
  if(LastMasterCommand == 'p'){ //projector UC18
    for(int i = 1; i <= i2c_regs[0]; i++)
      {
        Serial.println("Command: "+String(i2c_regs[1]));
        switch((char)i2c_regs[1])
          {
            case 'p': //power
            case 'P':
              irsend3.sendNEC(0xFD40BF, 32);
              Serial.println(" POWER ");
              break;
            case 'v': //volume down
              irsend3.sendNEC(0xFD6897, 32);
              break;
            case 'V': //volume up
              irsend3.sendNEC(0xFD48B7, 32);
              break;
            case 'i': //input
            case 'I':
              irsend3.sendNEC(0xFD609F, 32);
              break;
            case 'o': //ok
            case 'O':
              irsend3.sendNEC(0xFD906F, 32);
              break;
            case 'm': //mute
              irsend3.sendNEC(0xFD00FF, 32);
              break;
            case 'M': //menu
              irsend3.sendNEC(0xFD20DF, 32);
              break;
            case 'u': //up
            case 'U':
              irsend3.sendNEC(0xFDA05F, 32);
              break;
            case 'l': //left
            case 'L':
              irsend3.sendNEC(0xFD10EF, 32);
              break;
            case 'r': //right
            case 'R':
              irsend3.sendNEC(0xFD50AF, 32);
              break;
            case 'd': //down
            case 'D':
              irsend3.sendNEC(0xFDB04F, 32);
              break;
            case 'e': //esc
            case 'E':
              irsend3.sendNEC(0xFD8877, 32);
              break;
          }
        delay(40);
      }
  }
  if(LastMasterCommand == 'r'){ //any IR device
    //todo send raw code to pin 9
    irsend9.sendRaw(rawCodes, sizeof(rawCodes), 38); //todo
    for(int i = 0; i < reg_size2; i++)
      {
        rawCodes[i]=0;
      }
  }
  
  i2c_regs[0]='\0';
  rawCodes[0]='\0';
  LastMasterCommand = 0;
  Serial.println("");
  delay(1000);
}

/*
 * I2C Handelers
 */
void i2cReceiveEvent(uint8_t howMany)
{
  int reg_position = 0;
  if (howMany < 1)
    {
      return;// Sanity-check
    }
  //command
  LastMasterCommand = Wire.read();
  howMany--;
  if (!howMany)
    {
      return;// This write was only to set the buffer for next read
    }
  while(Wire.available())
    {
      //Store the recieved data in the currently selected register
      if(LastMasterCommand == 'p'){ //projector UC18
        i2c_regs[reg_position] = Wire.read();
        Serial.print(String(reg_position)+" - "+String(i2c_regs[reg_position])+" , ");
        //Proceed to the next register
        reg_position++;
        if (reg_position >= reg_size)
          {
            reg_position = 0;
          }
        i2c_regs[reg_position]='\0';
      }
      if(LastMasterCommand == 'r'){ //any IR device,  receive only 32bit TODO
        rawCodes[reg_position] = Wire.read() << 8 | Wire.read();
        Serial.print(String(reg_position)+" - "+String(rawCodes[reg_position])+" , ");
        //Proceed to the next register
        reg_position++;
        if (reg_position >= reg_size2)
          {
            reg_position = 0;
          }
        rawCodes[reg_position]='\0';
      }
    }
}//End i2cReceiveEvent()

void i2cRequestEvent()
{
  //Send the value on the current register position
  //NOT WORKING when requestin multiple bytes
  int n = reg_size - reg_position;//Number of registers to return
  for(int i = reg_position; i < n; i++)
    {//Return all bytes from the reg_position to the end
      Wire.write(i2c_regs[i]);
    }
  // Increment the reg position on each read, and loop back to zero
  reg_position++;
  if (reg_position >= reg_size)
    {
      reg_position = 0;
    } 
}//End i2cRequestEvent
