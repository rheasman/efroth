              **FROTH, a computer language to make espresso**

=FROTH a computer language to make espresso

==This is a work in progress, and no releases have been made yet

This is a super simple stack machine that makes espresso. Optimized so that it
can be implemented on the DE1 while using around 3 kB of RAM.

This is similar in some ways to the FORTH language, but not the same, so I'm
calling it the "FROTH" language.

This is a tiny (and impure) sibling of a "real" FORTH. It is FORTH-like, but a
lot less powerful than a real FORTH. On the other hand, it is hopefully easier
for non-technical people to use. In a real FORTH the compiler is always
running and advanced programmers add features to the language on the fly, so
they can implement object orientation, multitasking, first-class datatypes,
etc. as needed. In FROTH, the code is compiled once into a binary, and the
binary is run on the DE1, but the compiler can do a little more up-front
checking of the code as it sees it all at once.

This CPU works by reading things off a stack, processing them, and putting
them back onto the stack. It's called a stack because it's exactly like a
stack of plates, with the requirement that you are only allowed to touch the
top plate on the stack. If you put plates on the stack, then the only way to
take plates off the stack is in reverse order. In other words, a stack is
"Last In, First Out". The plate you can reach is the "Top of Stack" or "ToS".

So for example, the "+" operation, would read two values off the stack, add
them, and put one value back onto the stack.

The advantage of doing things this way is that you never need to specify where
things are coming from, or going to, and this saves a lot of space.

So, to add two numbers, you would execute:
```
	2   // Put 2 on the stack
	3   // Put 3 on the stack
	+   // Add the two numbers.
```
So, to encode "2*3 + 5*7" would be:
```
	2 3 * // Put 2 and 3 on the stack, then multiply them. 6 is now on the stack
	5 7 * // Put 5 and 7 on the stack and multiply them. 6 35 are now on the stack
	+     // Add the top two values on the stack, to get 41
```
And "2 + (3*5) + 7" would be:
```
	2      // Put 2 on the stack
	3 5 *  // Put 3 and 5, then multiply, stack now holds "2 15"
	7      // Put 7 on the stack, stack now holds "2 15 7"
	+      // Adds last two values, stack now holds "2 22"
	+      // Adds last two values, stack now holds "24"
```
Of course you could write that as "2 3 * 5 7 * +" and "2 3 5 * 7 + +" if you
wanted to. Note that no brackets are required, and it's alway exactly 7
operations to describe how those numbers are added; no brackets are required
to set ordering. This works because the operators (+, -, *, etc) are "postfix"
operators. They are the verbs that go after the objects. If the operators go
between the objects, we call them "infix" operators.

This way of representing operations is called "Reverse Polish Notation" or
"RPN". This name is very strange to me. It implies that things are being done
backwards. Perhaps this is because English speakers are used to "subject verb
object" and this works as "subject object verb". For symmetry I think we
should call the infix way of doing things "Weird English Notation" or "WEN".
Most people are used to WEN programming languages, but we won't hold this
against them.

Stack Descriptions
------------------

It's useful to be able to tersely specify how an operation works on a stack.
This is done using stack descriptions. There are two halves to a stack
description. The half before the "--" is the state of the stack before
anything happens, and the half after the "--" is what the stack looks like
when the operation is done. The rightmost item is the ToS.

Get used to stack descriptions as they are a clean and powerful way to
describe your code.

So, 'x -- (x+1)' means that 'x' is on the stack before the operation, and
'x+1' is on the stack after the operation.

For the '+' used above, the description would be 'a b -- (a+b)'. There are two
items on the stack before, a and b, and after "+" runs, there is one item, and
it is (a+b).

CPU Opcodes
-----------

An opcode is an instruction to the CPU. An "operation code". Computers process
numbers, so we use a number to represent a thing the CPU could do. "0" could
mean "+", "1" could be "/", "2" could be "-", etc.

The CPU executes a stream of opcodes. Each opcode is 1 byte, except for:
  * PCIMMS   : 2 bytes. Opcode + a single signed byte
  * IMMS     : 2 bytes. Opcode + a single signed byte.
  * IMMU     : 3 bytes. Opcode + two bytes representing a 16-bit unsigned number
  * IMMF     : 5 bytes. Opcode + 32-bit float immediate to be loaded onto the stack.

All internal arithmetic operations in this CPU are on floats, and the stack
holds floats only. A float is a number with a decimal point. The point can
move around, so it's a "floating point" number, which is where this silly and
unexpected name comes from. For example, "2.0", "0.2", "0.0002", "20.0".
Floats are great because they can describe numbers that are not integers.
People program with integers all the time, but it's annoying and not for
beginners. Representing the root of 2 using integers is a pain, for example.
In fact, behind the scene, floats are actually implemented using integers, but
it's all nicely hidden from you (mostly).

If an integer value is needed, say for bitwise operations, the float is
rounded to the nearest integer for the operation, then converted back to a
float. Be aware that a 32-bit float can only represent 24 bits of an integer
exactly, so keep bitwise integer operations at or below this number of bits if
you don't want to think about possible issues. Floats have issues for exact
arithmetic, but I decided that they would be easier for non-technical people
to use for our use cases.

Basics
------

Opcode Name | Stack Inputs "--" Stack Outputs | Comments 
:-----------|:--------------------------------|----------
DUP    |x -- x x         | Duplicate value on top of stack.
DROP   |x y -- x         | Discard TOS.
OVER   |x y -- x y x     | Duplicates the value at TOS-1. (Call twice to duplicate both values)
SWAP   |x y -- y x       | Swap x and y.
COPY   |x -- Stack[-x]   | Copy value(s) out of the stack at position TOS - x. Every 4 bits corresponds to an item.
ROT    |a b c -- b c a   | Rotate top 3 values of stack around. Move beginning to end.
NROT   |a b c -- c a b   | Rotate top 3 values of stack around. Move end to beginning.
       |                 |
+      |x y -- (x+y)     | Add x and y.
-      |x y -- (x-y)     | Subtract y from x.
*      |x y -- (x*y)     | Multiply x and y.
/      |x y -- (x/y)     | Divide x by y.
       |                 |
POW    |x y -- pow(x,y)  | Take x to the power of y.
NEG    |x -- (-x)        | Invert sign of TOS.
REC    |x -- (1/x)       | Reciprocal of TOS.
       |                 |
TZ     |x -- (1 or 0)    | Test Zero.  TOS = 1 if x  = 0, else 0
TGT    |x y -- (x&gt;y)     | Test Greater Than.  TOS = 1 if x  &gt; y, else 0
TLT    |x y -- (x&lt;y)     | Test Less Than. TOS = 1 if x  &lt; y, else 0
TGE    |x y -- (x&gt;=y)    | Test Greater or Equal.  TOS = 1 if x &gt;= y, else 0
TLE    |x y -- (x&lt;=y)    | Test Less or Equal. TOS = 1 if x &lt;= y, else 0
TIN    |x -- (1 or 0)    | Test Invalid Number. TOS = 1 if x is NaN or Inf
       |                 |
OR     |x y -- (x  OR y) | Bitwise integer OR. Note that a FLOAT32 can only represent up to 24-bit integers exactly.
AND    |x y -- (x AND y) | Bitwise integer AND
XOR    |x y -- (x XOR y) | Bitwise integer XOR
BINV   |x   -- (~x)      | Bitwise Inverse. x is rounded to the nearest integer before the operation
       |                 |
BNZ    |x a --           | Branch to a if x != 0.
BZ     |x a --           | Branch to a if x == 0.
BRA    |a   --           | Branch to a.
       |                 |
CALL   |x                | Execute word x.
;      |                 | Returns to calling word. Use at end of word only.
EXIT   |                 | Returns to calling word. Use in middle of words, only.
WAIT   |                 | Sleep until the start of the next AC cycle.
NOP    |                 | Does nothing.
       |                 |
TOR    |x  --            | Pop x and push to Return Stack
FROMR  |-- x             | Pop from Return Stack and push to ToS
COPYR  |a -- x           | Copy value at index [a] on Return Stack to ToS (TODO)
       |                 |
PCIMMS |# -- x           | Push PC + # onto the stack.
IMM    |# -- x           | Push an immediate value from (0..127) onto the stack.
IMMS   |# -- x           | Push an immediate value from (-127 to 128) onto the stack.
IMMU   |# -- x           | Push an immediate value from (0 to 65536) onto the stack.
IMMF   |# -- x           | Push an immediate single-precision float (32-bit) onto the stack.
       |                 |
!      |x y -- [y] = x       | Store x at address y.
@      |y   -- [y]             | Fetch a value from address y, put it on the stack.
       |                 |
!B     |x y -- [y] = x   | Convert x to a single byte and store it at address y.
@B     |y -- [y]         | Load a single byte from position y in the packet store.
       |                 |
TXP    |-- x             | Send a packet if possible. Return 1 if sent, 0 if dropped.
RXP?   | -- x            | Return 1 if a packet arrived, else zero. PacketData RX area is not modified until this is called.
       |                 |
IOR    |x -- IO[x]       | Read value of type x. (Reads state or sensor)
IOW    |x y --           | Put value x to control y. (Commands a state or target value)
IORT   |x -- LastIO[x]   | Read last value written to y. (Reads back what the machine actually accepted)
### Comments
FROTH uses "//" to start a comment. The compiler ignores everything after a
"//". Humans use these to leave notes about what they are doing, in their
code, beause humans forget things and are so dumb they even have to explain
their own code to themselves.

### Words
A word is a command to the CPU do something. In fact, "opcodes" are just words
built into the CPU. We can define new words, which are just collections of
words themselves. We call this collection of words a dictionary.

FROTH uses ":" to define a new word entry and ";" to end a definition. For example:
```
    : AddOne 1 + ;  // x -- (x+1)
```
Using this word will put 1 on the stack, then do an add, then go on to the
next word. Words can be layered on top of each other.
```
    : StupidAddThree AddOne AddOne AddOne ; // x -- (x+3)
```

Using this word will add 3 to the top of the stack, in a particularly dumb
way. But it shows how you can make words out of other words.

#### Details on Special Words
Skip this section if you are beginner. :-)

__IMM__ is a virtual opcode in that any opcode with the top bit set is seen as a
7-bit unsigned immediate value. So it's actually 128 opcodes, which represent
the numbers 0 through 128.

__FOR__ is used to implement the beginning of a FOR loop. {} is used to represent
the control stack:
```
    FOR limit step index nextblockaddr
      -- {limit step index startaddr}      // Index is inside limits
```
 or
```
    FOR limit step index nextblockaddr
      -- ; PC = nextblockaddr    // Index is outside limits
```
__FOR__ copies the limit, step, and start of the loop variables onto the control
stack, if the start index is inside the range, otherwise it branches to
nextblockaddr. Either way, it consumes nextblockaddr.

__INDEX__ copies the xth index out of the control stack, onto the ToS. 0 is the
innermost loop index:
```
    INDEX  x {limit1 step1 index1 addr1 limit0 step0 index0 addr1}
      -- {limit1 step1 index1 addr1 limit0 step0 index0 addr0} index_x
```
__ENDFOR__ is used to implement the end of a __FOR__ loop. It adds the step to the
index and checks against the limit. If the index is out of range, it removes
the control information from the stack and goes to the next instruction.
Otherwise, it branches back to startaddr:
```
    ENDFOR {limit step index startaddr}
      -- {limit step index+step startaddr} ; PC = startaddr
```
 or
``` 
    ENDFOR {limit step index startaddr} -- {}; PC = PC+1
```
### Stacks
There are two stacks in this virtual CPU. They are the Data Stack and the Control
Stack. The control stack remembers return addresses when a word is called
(this stack can also be called the "return stack" or the "call stack"). It
also holds control variables for loops. The data stack is for everything else.

So, if the word "StupidAddThree" calls "AddOne", then the CPU's place in the
word is remembered on the call stack while the "AddOne" words are being
executed.


## Higher level language features


As time goes on, I will add more of these. They are typically implemented in
the FROTH compiler, rather than being directly implemented with words. You
write these structures, and the compiler converts them to words.

For now, I have implemented:
```
    IF ... ENDIF 
    IF ... ELSE ... ENDIF
```
Still to do, maybe:
```
    REPEAT ... ENDREPEAT
    WHILE ... ENDWHILE
    CONST
```

## Program Executable Layout

The general format for a program binary is:
```
  Header
  Vectors
  Words (Program ROM)
```

### Header:
A program starts with a max volume and a max number of seconds, for safety.
The header also version numbers and other useful bits.

### Vectors: 
This is a list of words that are called in special circumstances.

I'm not sure what vectors make sense, and will add to them over time.

For now, there three vectors:

Vector | Use
-------|-----
SHOT   | The word address called when a shot is started.
IDLE   | The word address called when the machine is idle and needs to set a group idle  temperature and tank preheat temperature.
HALT   | The word address called when something has forced a halt of the SHOT program. Should be used to do clean up if necessary.
HOTW   | The word called when hot water is requested. Not used if 0.

### Words:
A word is a list of opcodes that returns when done. Basically, a function that
accepts a stack and that can modify it. You can have up to 256 words, and all
words together should take less than 1024 bytes.

The last word defined is executed to start the program.

## Program execution environment

Every second, the machine will execute a limited number of opcodes. This limit
is still to be determined.

### Memory Map

While the program is running, this is the memory layout:

Name        | Address Dec | Address Hex   | RW | Use
------------|-------------|---------------|----|-----
Scratch RAM |    0 -  255 | 0000 - 0100   | RW | 64 Floats or 256 Bytes of R/W memory
Packet RX   | 4096 - 4111 | 1000 - 100F   | R  | Received packet, 16 bytes
Packet TX   | 4112 - 4127 | 1010 - 101F   | W  | Transmit packet, 16 bytes
Profile ROM | 4128 - 8191 | 1020 - 1FFF   | R  | Profile settings received over BLE
Program RAM | 8192 - 9215 | 2000 - 23FF   | RW | Program RAM, 1024 bytes

Note that program RAM is written and read from address base 0X2000, but is
executed at address 0. This is so that accesses to scratch RAM, and
branch/call targets can be encoded cheaply.

#### Packet data:

There is space for a packet of data to be sent, and a packet of data to be
received. Each packet is exactly 16 bytes long. All bytes are sent or
received.

The RX packet area is read only, and the TX packet area is write only.

The TXP opcode sends the contents of the TX packet area. 

The RXP? opcode checks to see if there is a packet available, and copies it
into the RX area if so. It returns 1 if there is a new packet, else zero.

#### The IO Region

This is the region used to control and respond to the espresso machine. It is
adjacent to the main memory map in that it is only accessible using the IOR,
IOW, and IORT opcodes.

Doing a IOR reads a sensor value, or the current state of the machine. IOW
commands a state or asks that a sensor value be targeted.

For example, writing "10" to "Pressure" sets 10 as a target pressure to reach.
An IOR of "Pressure" will return the current pressure, and IORT will return
"10" telling you what it thinks the target is that you requested. Writing to
slots that make no sense will halt your program. Writing an out of range value
will silently clamp the value to the allowed range, and you'll be able to see
this clamping if you use IORT to read back your write.

The currently defined IO consts are:

Value | Name          | RWT | Use
------|---------------|-----|----
0 | IO_Pressure       | RWT | Pressure
1 | IO_Flow           | RWT | Flow
2 | IO_ShowerTemp     | RWT | Shower Temp
3 | IO_GroupMetalTemp | RWT | Group head temperature
4 | IO_GroupInletTemp | RWT | Fluid temperature at the group head inlet
5 | IO_Vol            | RWT | Estimated volume since start of shot
6 | IO_NumSeconds     | RWT | Time since start of shot
7 | IO_ReportedState  | RWT | Substate we last reported

#### The Profile Region

This is a read-only view on the profile data sent over BLE to the machine, for
current normal and advanced profiles. The FROTH script may opt to read from
this area so that it can sequence shots using the settings stored here.

The FROTH Language
------------------

Your job as the programmer is to define the words that will be executed.

Each program will start with `"Program(Name, MaxVol, MaxSecs)"`. `MaxVol` and
`MaxSecs` are safety limits that the DE1 will not let the program exceed.

There are a few reserved words. All opcodes, and `":"` and `";"`.

__:__ means define a word.

__;__ means compile a word and add it to the dictionary.

__;(__ is the same as ";", but adds extra information for debugging.

__{Label}__ means define a point that can be branched to.

Angle bracket tags (for example `<Name>`) add debug information for the
debugger. They provide a symbolic name for the ToS. The CPU never sees this,
but the Delgona debugger sees this information so that it can describe the
stack better for you.

Any number will be encoded using the shortest appropriate IMM opcode.

There are convenience words defined for IO slots. Each will start with "IO_".

Comments start with "//". The compiler ignores them.

Here is a (NOW OBSOLETE) example. Some features have changed, and others have
been added. It's still fairly close though:

```
Program("Simple flat 9 bar 30s 92.5C shot", 500, 120)

: SetPressure  // Define word "SetPressure" to set the machine pressure
  IO_Pressure  // Put constant referring to Pressure on stack
  IOW          // Write pressure to DE1
  ;

: SetTemp       // Define word "SetTemp" to set the machine shower head and group temperature
  DUP           // Make a copy of the temperature
  IO_ShowerTemp // Put constant referring to shower head temperature on stack
  IOW           // Set target temp
  IO_GroupTemp  // Group head metal temperature
  IOW           // Set target temp
  ;

: GetSeconds     // Get number of seconds elapsed since start of shot
  IO_NumSeconds  // Put constant referring to number of seconds since start of shot on stack
  IOR            // Read number of seconds
  ; 

: SecsReached    // Return 1 if we've reached the given number of seconds
  GetSeconds     // x secs   Get the number of seconds elapsed
  SWAP           // secs x   Swap x and seconds
  TGE            // (secs&gt;=x) 1 if seconds &gt; x, else 0
  ; // Return 1 if we've reached the end of the shot

: EndTheShot // Tell the DE1 to stop
  IO_EndShot
  1
  IOW
  ;

// Define the actual shot
: Shot
  92.5 SetTemp    // Set group temperature to 92.5 deg C
  9 SetPressure   // Set the pressure target
{NotDoneYet}      // Define a label
  WAIT            // Wait until next AC Cycle
  30 SecsReached  // Returns 1 if seconds reached, else zero
  NotDoneYet BZ   // Jump to label if seconds not reached
  EndTheShot      // Tell DE1 to stop

```

Note that this could have been written as follows, with no change in meaning:
```
Program("Simple flat 9 bar 30s 92C shot", 500, 120)

: SetPressure IO_Pressure IOW ;
: SetTemp DUP IO_ShowerTemp IOW IO_GroupTemp IOW ;
: GetSeconds IO_NumSeconds IOR ; 
: SecsReached GetSeconds SWAP TGE ;
: EndTheShot IO_EndShot 1 IOW ;

// Define the actual shot
: Shot
  92.5 SetTemp     // Set group temperature to 92.5 deg C
  9 SetPressure    // Set the pressure target
{NotDoneYet}       // Define a label
  WAIT             // Wait until next AC Cycle
  30 SecsReached   // Returns 1 if seconds reached, else zero
  BZ NotDoneYet    // Jump to label if seconds not reached
  EndTheShot       // Tell DE1 to stop
```
This program takes around 40 bytes of memory in total.

## Adding Features for Debugging

The extended debugging format for a word will look like this:
```
:(SLength -- ReachedBool) SecsReached
```
Everything in the brackets is used to create debug information for the
debugger. In the debugger, the different stack positions will use the names
given, during single step debugging. The compiled code will not use the extra
information.

Also, the programmer can insert tags anywhere, and they are used to describe the ToS.

For example:
```
: GetSeconds     // Get number of seconds elapsed since start of shot
  IO_NumSeconds  // Put constant referring to number of seconds since start of shot on stack
  IOR            // Read number of seconds
  &lt;Seconds&gt;
  ; 
```
The debugger will call the stack element associated with the return value from
this word "Seconds". THe CPU will be completely unaware of this, as none of
this information is passed to it. This is just extra information for human
consumption.

Binary Format
-------------

The binary format will be as follows. All numbers are little endian.

Address     | Use
------------| ---
0000 - 0003 | 'EFVM'
0004 - 0005 | Version. U16. 0 for this layout
0006 - 0007 | MaxVol (ml),  1 - 1024
0008 - 0009 | MaxSec ( s),  1 - 600
000A - 000B | ROM Start. The start of the program ROM, as a byte offset into the file.
000C - 000D | Vector: SHOT : Start address for execution of a shot. 0 means not used.
000E - 000F | Vector: IDLE : Called to set group and preheat temps. 0 means not used.
0010 - 0011 | Vector: HALT : Called to cleanup a shot if an error occurs. 0 means not used.
xxxx - xxxx | Length of program ROM in bytes.
000E - xxxx | Program ROM

# TODO

These are things I am working on.

  * Move all store and fetch operations to the same memory space.

<!-- Markdeep: -->
<style class="fallback">body{visibility:hidden;white-space:pre;font-family:monospace}</style>
<script src="markdeep.min.js" charset="utf-8"></script>
<script src="https://morgan3d.github.io/markdeep/latest/markdeep.min.js" charset="utf-8"></script>
<script>window.alreadyProcessedMarkdeep||(document.body.style.visibility="visible")</script>