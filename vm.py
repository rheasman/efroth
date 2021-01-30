#!/usr/bin/env python3
from collections import deque
from opcodes import OpCodes
import array, math, struct, sys

def toF32(x):
  print(x)
  return struct.unpack('f', struct.pack('f', float(x)))[0]

class F32Stack:
  """
  A stack implemented on top of a deque, so we can
  catch under and overflow cleanly
  """
  def __init__(self, size, callbackover, callbackunder):
    self.Stack = deque()
    self.Size = size
    self.CallbackO = callbackover
    self.CallbackU = callbackunder
    self.Changed = True

  def __len__(self):
    return len(self.Stack)

  def read(self, pos):
    """
    Non-destructive read of item on stack.

    0 = TOS
    1 = TOS-1
    2 = ToS-2, etc
    """
    pos += 1
    if len(self.Stack) < pos:
      self.CallbackU()

    return self.Stack[-pos]

  def peek(self, x):
    return self.read(0)

  def push(self, x):
    if len(self.Stack) >= self.Size:
      self.CallbackO()

    x = toF32(x)
    self.Stack.append(x) # Append to right of stack
    self.Changed = True

  def pop(self):
    if len(self.Stack) <= 0:
      self.CallbackU()

    self.Changed = True
    return self.Stack.pop(x) # Pop off right of stack

  def pop2(self):
    b = self.pop()
    a = self.pop()
    self.Changed = True
    return (a, b)

class CPU:
  def __init__(self):
    self.ROM = array.array('B', [0]*1024)
    self.CallStack = F32Stack(64, self.stackErrorCB, self.stackErrorCB)
    self.Stack = F32Stack(64, self.stackErrorCB, self.stackErrorCB)
    self.ControlStack = F32Stack(64, self.stackErrorCB, self.stackErrorCB)
    self.PC = 0
    self.Globals = array.array('f', [0.0]*64)
    self.RXPacket = array.array('B', [0]*16)
    self.TXPacket = array.array('B', [0]*16)
    self.Opcodes = OpCodes()

  def loadRaw(self, filename):
    f = open(filename, 'rb')
    rom = f.read()
    f.close()
    for i, x in enumerate(rom):
      self.ROM[i] = x

    self.PC = 21

  def stackErrorCB(self):
    print("Stack error")
    asdf
    sys.exit(1)

  def step(self):
    opsize = 1
    opcode = self.ROM[self.PC]
    if (opcode & 0x80):
      # It's an immediate unsigned 7 bit literal
      self.IMM(opcode & 0x7F)
    else:
      opname = self.Opcodes.OPCODENAME[opcode]
      if opname in self.Opcodes.LONGEROPCODES:
        # One of the immediate instructions
        opsize = self.Opcodes.LONGEROPCODES[opname]
        daddr = self.PC+1
        if opname == 'PCIMMS':
          val = self.ROM[daddr] + self.PC - 128
          self.IMM(val)

        if opname == "IMMS":
          val = self.ROM[daddr] - 128
          self.IMM(val)

        if opname == "IMMU":
          val = self.ROM[daddr] | (self.ROM[daddr+1] << 8)
          self.IMM(val)

        if opname == "IMMF":
          val = struct.unpack("<f", self.ROM[daddr:daddr+4])[0]
          self.IMM(val)

    self.PC += opsize


  """
  OPCODES START HERE
  """

  def DUP(self):
    # DUP   x -- x x
    self.Stack.push(self.Stack.pop())

  def DROP(self):
    # DROP  x y -- x
    self.Stack.pop()

  def OVER(self):
    # OVER  x y -- x y x
    self.Stack.push(self.Stack.read(1))

  def SWAP(self):
    # SWAP  x y -- y x
    x,y = self.Stack.pop2()
    self.Stack.push(y)
    self.Stack.push(x)

  def COPY(self):
    # COPY  x -- Stack[-x] (0 is the item before x, etc)
    x = self.Stack.pop()
    self.Stack.push(self.Stack.read(x))

  def PLUS(self):
    # +     x y -- (x+y)
    x, y = self.Stack.pop2()
    self.Stack.push(x+y)

  def MINUS(self):
    # -     x y -- (x-y)
    x, y = self.Stack.pop2()
    self.Stack.push(x-y)

  def TIMES(self):
    # *     x y -- (x*y)
    x, y = self.Stack.pop2()
    self.Stack.push(x*y)    

  def DIV(self):
    # /     x y -- (x/y)
    x, y = self.Stack.pop2()
    self.Stack.push(x/y)

  def POW(self):
    # POW   x y -- pow(x,y)
    x, y = self.Stack.pop2()
    self.Stack.push(math.pow(x, y))

  def NEG(self):
    # NEG   x -- (-x)        : Invert sign of TOS.
    x = self.Stack.pop()
    self.Stack.push(-x)

  def REC(self):
    # REC   x -- (1/x)       : Reciprocal of TOS.
    x = self.Stack.pop()
    self.Stack.push(1.0/x)

  def TZ(self):
    # TZ    x -- 1|0         : Test Zero.  TOS = 1 if x  = 0, else 0
    x = self.Stack.pop()
    if x == 0:
      self.Stack.push(1.0)
    else:
      self.Stack.push(0.0)

  def TGT(self):
    # TGT   x y -- (x>y)     : Test Greater Than.  TOS = 1 if x  > y, else 0
    x, y = self.Stack.pop2()
    if x > y:
      self.Stack.push(1.0)
    else:
      self.Stack.push(0.0)

  def TLT(self):
    # TLT   x y -- (x<y)     : Test Less Than. TOS = 1 if x  < y, else 0
    x, y = self.Stack.pop2()
    if x < y:
      self.Stack.push(1.0)
    else:
      self.Stack.push(0.0)

  def TGE(self):
    # TGE   x y -- (x>=y)    : Test Greater or Equal.  TOS = 1 if x >= y, else 0
    x, y = self.Stack.pop2()
    if x >= y:
      self.Stack.push(1.0)
    else:
      self.Stack.push(0.0)

  def TLE(self):
    # TLE   x y -- (x<=y)    : Test Less or Equal. TOS = 1 if x <= y, else 0
    x, y = self.Stack.pop2()
    if x <= y:
      self.Stack.push(1.0)
    else:
      self.Stack.push(0.0)

  def TIN(self):
    # TIN   x -- 1|0         : Test Invalid Number. TOS = 1 if x is NaN or Inf
    x = self.Stack.pop()
    if math.isnan(x) or math.isinf(x):
      self.Stack.push(1.0)
    else:
      self.Stack.push(0.0)

  def OR(self):
    # OR    x y -- (x OR y) : Bitwise integer OR
    x, y = self.Stack.pop2()
    x = int(round(x))
    y = int(round(y))
    self.Stack.push(x | y) # Push converts everything to a float32

  def AND(self):
    # AND   x y -- (x AND y) : Bitwise integer AND
    x, y = self.Stack.pop2()
    x = int(round(x))
    y = int(round(y))
    self.Stack.push(x & y) # Push converts everything to a float32

  def XOR(self):
    # XOR   x y -- (x XOR y) : Bitwise integer XOR
    x, y = self.Stack.pop2()
    x = int(round(x))
    y = int(round(y))
    self.Stack.push(x ^ y) # Push converts everything to a float32

  def BINV(self):
    # BINV  x   -- (~x)      : Bitwise Inverse. Treats x as an integer
    x = self.Stack.pop()
    x = int(round(x))
    self.Stack.push(~x)

  def BNZ(self):
    # BNZ   x a --           : Branch to a if x != 0. 
    x, a = self.Stack.pop2()
    if x != 0:
      self.PC = int(round(a))

  def BZ(self):
    # BZ    x a --           : Branch to a if x == 0.
    x, a = self.Stack.pop2()
    if x == 0:
      self.PC = int(round(a))

  def BRA(self):
    # BRA   a   --           : Branch to a.
    a = self.Stack.pop()
    self.PC = int(round(a))

  def CALL(self):
    # CALL  x                : Execute word x.
    self.CallStack.push(self.PC)  # PC should already be pointing to the next instruction
    self.PC = int(round(a))

  def RET(self):
    # ;                      : Returns to calling word.
    a = self.CallStack.pop()
    self.PC = int(round(a))

  def WAIT(self):
    # WAIT                   : Sleep until the start of the next AC cycle.
    pass

  def NOP(self):
    # NOP                    : Does nothing.
    pass

  def PCIMMS(self, imm):
    # PCIMMS # -- x          : Push PC + # onto the stack.
    x = self.PC + imm - 1    # PC has been pre-incremented, so subract 1
    self.Stack.push(x)

  def IMM(self, imm):
    # IMM    # -- x          : Push an immediate value from (0..127) onto the stack.
    # IMMS   # -- x          : Push an immediate value from (-127 to 128) onto the stack.
    # IMMF   # -- x          : Push an immediate single-precision float (32-bit) onto the stack.
    self.Stack.push(imm)

  def STORE(self):
    # STORE x y -- [y] = x   : Store x in slot y.
    x, y = self.Stack.pop2()
    self.Globals[y] = x

  def FETCH(self):
    # FETCH y -- [y]         : Fetch a value from slot y, put it on the stack.
    y = self.Stack.pop()
    self.Stack.push(self.Globals[y])

  def PS(self):
    # PS    x y -- [y] = x   : Convert x to a single byte and store it at packet offset y.
    x, y = self.Stack.pop2()
    self.TXPacket[y] = int(round(y))

  def PF(self):
    # PF    y -- [y]         : Load a single byte from position y in the packet store.
    y = self.Stack.pop()
    self.Stack.push(self.RXPacket[y])

  def TXP(self):
    # TXP     -- x           : Send a packet if possible. Return 1 if sent, 0 if dropped.
    self.Stack.push(1.0)

  def RXP(self):
    # RXP?    -- x           : Return 1 if a packet arrived, else zero. PacketData RX area is not modified until this is called.
    self.Stack.push(1.0)    

  def IOR(self):
    # IOR   x -- v           : Read value of type x. (Reads state or sensor)
    x = self.Stack.pop()
    self.ioRead(x)

  def IOW(self):
    # IOW   x y --           : Put value x to control y. (Commands a state or target value)
    x, y = self.Stack.pop2()
    self.ioWrite(x, y)

  def IORT(self):
    # IORT  y -- x         : Read last value written to y. (Reads back a command)
    x = self.Stack.pop()
    self.Stack.push(self.ioReadTarget(x))

