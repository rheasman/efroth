#!/usr/bin/env python3
from collections import deque, namedtuple
from opcodes import OpCodes
import array, math, struct, sys
from disasm import DebugDis
import ioconsts

SEntry = namedtuple("SEntry", "float, symbol")

def toF32(x):
  #print(x)
  return struct.unpack('f', struct.pack('f', float(x)))[0]

def toFBytes(x):
  return struct.pack('<f', x)

def floatFromBytes(x):
  return struct.unpack('<f', x)[0]

class F32Stack:
  """
  A stack implemented on top of a deque, so we can
  catch under and overflow cleanly.
  """
  def __init__(self, size, callbackover, callbackunder):
    self.Stack = deque()
    self.Size = size
    self.CallbackO = callbackover
    self.CallbackU = callbackunder
    self.Changed = True

  def reset(self):
    self.Stack = deque()

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

    x._replace(float=toF32(x.float))
    self.Stack.append(x) # Append to right of stack
    self.Changed = True

  def pop(self):
    if len(self.Stack) <= 0:
      self.CallbackU()

    self.Changed = True
    return self.Stack.pop() # Pop off right of stack

  def pop2(self):
    b = self.pop()
    a = self.pop()
    self.Changed = True
    return (a, b)

class DE1Sim:
  """
  Simulates the rest of the machine outside the CPU
  """
  def __init__(self, systime):
    self.SysTime = systime
    self.IOConsts = ioconsts.IOConsts()

    self.Pressure = 0.0
    self.Flow = 0.0
    self.GroupMetalTemp  = 0.0
    self.ShowerTemp = 0.0

    self.PressureTarget = 0.0
    self.FlowTarget = None
    self.GroupMetalTempTarget = 0.0
    self.ShowerTempTarget = 0.0

  def startShot(self):
    self.NumMS = 0

  def step(self):
    if self.PressureTarget != None:
      self.Pressure = 0.99*self.Pressure + 0.01*self.PressureTarget

    if self.FlowTarget != None:
      self.Flow = 0.99*self.Flow + 0.01*self.FlowTarget

    self.ShowerTemp = 0.99*self.ShowerTemp + 0.01*self.ShowerTempTarget

  def clamp(self, x, minx, maxx):
    if x < minx:
      x = minx

    if x > maxx:
      x = maxx

    return x

  def ioWrite(self, x, y):
    name = self.IOConsts.IOCONSTNAME[int(round(y.float))]
    print(f"ioWrite of {x} to {name}")
    permissions = self.IOConsts.IODICT[name]
    if 'W' in permissions:
      getattr(self, f"{name}W")(x.float)

  def ioRead(self, y):
    name = self.IOConsts.IOCONSTNAME[int(round(y.float))]
    print("ioRead from ", name, end='')
    permissions = self.IOConsts.IODICT[name]
    if 'R' in permissions:
      res = getattr(self, f"{name}R")()
      print(": ", res)
      return res

  def IO_PressureW(self, x):
    #("IO_Pressure"         , "RWT"),  # R = Readable. W = Writeable. T = Can read back
    self.FlowTarget = None
    x = self.clamp(x, 0.0, 12.0)

    self.PressureTarget = x

  def IO_PressureR(self):
    return SEntry(self.Pressure, "Pressure")

  def IO_PressureT(self):
    if self.PressureTarget == None:
      return SEntry(-1, "PressureTarget")

    return SEntry(self.PressureTarget, "PressureTarget")

  def IO_ShowerTempW(self, x):
    x = self.clamp(x, 0.20, 105.0)
    self.ShowerTempTarget = x

  def IO_ShowerTempR(self):
    return SEntry(self.ShowerTemp, "ShowerTemp")

  def IO_ShowerTempT(self):
    return SEntry(self.ShowerTempTarget, "ShowerTempTarget")

  def IO_GroupMetalTempW(self, x):
    x = self.clamp(x, 0.20, 105.0)
    self.GroupMetalTempTarget = x

  def IO_GroupMetalTempR(self):
    return SEntry(self.GroupMetalTemp, "GroupMetalTemp")

  def IO_GroupMetalTempT(self):
    return SEntry(self.GroupMetalTempTarget, "GroupMetalTempTarget")

  def IO_NumSecondsR(self):
    return SEntry(self.SysTime.getS(), "NumSeconds")






  """  
    ("IO_Flow"             , "RWT"),
    ("IO_ShowerTemp"       , "RWT"),
    ("IO_GroupMetalTemp"   , "RWT"),
    ("IO_GroupInletTemp"   , "RWT"),
    ("IO_Vol"              , "R"),
    ("IO_NumSeconds"       , "R"),
    ("IO_EndShot"          , "W")
  """

class VMCPUException(Exception):
  pass

class VMCPUMemAccessError(VMCPUException):
  pass # Read/Write to bad address
  
class VMCPUInvalidWrite(VMCPUMemAccessError):
  pass # Write to invalid address

class VMCPUInvalidRead(VMCPUMemAccessError):
  pass # Read from invalid address

class VMCPUInfo(VMCPUException):
  pass # Informational exceptions. Mostly used by debugger.

class VMCPUBreakpoint(VMCPUInfo):
  pass

class VMCPUStopped(VMCPUInfo):
  """
  Tell the caller that the CPU has executed the STOP opcode
  """
  pass

class StackError(VMCPUException):
  pass

class StackUnderflow(StackError):
  pass

class StackOverflow(StackError):
  pass

class CPU:
  Opcodes = OpCodes()
  OpMap = {
    '+'  : 'PLUS',
    '-'  : 'MINUS',
    '*'  : 'TIMES',
    '/'  : 'DIV',
    ';'  : 'RET',
    '!'  : 'STORE',
    '@'  : 'FETCH',
    '!B' : 'STOREB',
    '@B' : 'FETCHB',
  }
  def __init__(self, systime):
    self.SysTime = systime
    self.Sim = DE1Sim(systime)
    self.ROM = array.array('B', [0]*1024)
    self.CallStack = F32Stack(64, self.stackErrorOCB, self.stackErrorUCB)
    self.Stack = F32Stack(64, self.stackErrorOCB, self.stackErrorUCB)
    self.ControlStack = F32Stack(64, self.stackErrorOCB, self.stackErrorUCB)
    self.Scratch = array.array('B', [0]*256)
    self.RXPacket = array.array('B', [0]*16)
    self.TXPacket = array.array('B', [0]*16)

    self.reset()

  # def loadRaw(self, filename):
  #   f = open(filename, 'rb')
  #   rom = f.read()
  #   f.close()
  #   for i, x in enumerate(rom):
  #     self.ROM[i] = x

  #   self.PC = 21

  def reset(self):
    self.memClear()

    self.PC = 0
    self.Cycles = 0
    self.Stopped = 0
    self.Stack.reset()
    self.CallStack.reset()
    self.BreakPoints = set()
    self.Stopped = False
    self.MemWriteList = []

    # Store the symbols of addresses written to, in format (addrsymbol, datasymbol, type).
    # Type is float or byte, 'f' or 'b'
    self.MemAddrSymbols = {} 

  def memClear(self):
    for i in range(256):
      self.Scratch[i] = 0

    for i in range(16):
      self.TXPacket[i] = 0      
      self.RXPacket[i] = 0      

  def moveToWord(self, word):
    if word in self.D.Words:
      self.PC = self.D.Words[word][1]

  def loadDebug(self, filename):
    self.D = DebugDis(filename)
    self.ROM = array.array('B', self.D.MemBytes)
    self.reset()

  def toggleBP(self, addr):
    if addr in self.BreakPoints:
      self.BreakPoints.remove(addr)
    else:
      self.BreakPoints.add(addr)

  def isBP(self, addr):
    return addr in self.BreakPoints

  def stackErrorUCB(self):
    raise StackUnderflow('Stack underflow')

  def stackErrorOCB(self):
    raise StackOverflow('Stack overflow')

  def getOpcodeName(self, opcode):
    if opcode & 0x80:
      return "IMM"

    return self.Opcodes.OPCODENAME[opcode]

  def getMemWriteList(self):
    return self.MemWriteList

  def clearMemWriteList(self):
    self.MemWriteList = []

  def getCurrentOpcodeName(self):
    opcode = self.ROM[self.PC]
    return self.getOpcodeName(opcode)

  def isCurrentOpCall(self):
    opcode = self.ROM[self.PC]
    if opcode & 0x80:
      return False

    opname = self.Opcodes.OPCODENAME[opcode]
    if opname == "CALL":
      return True

    return False

  def nextOpcodeAddr(self, addr):
    # Return the address after the current opcode
    return addr + self.Opcodes.opcodeLen(addr)

  def runUntilBreakpoint(self):
    while self.PC not in self.BreakPoints:
      self.step()

  def step(self, ignorebp=None):
    if self.Stopped:
      raise VMCPUStopped('CPU is stopped')

    if self.PC in self.BreakPoints:
      if self.PC != ignorebp:
        raise VMCPUBreakpoint('Breakpoint hit')

    self.Cycles += 1
    self.SysTime.addTicks(1)  # 1 tick per opcode, for now
    opsize = 1
    opcode = self.ROM[self.PC]
    if self.Opcodes.isImmediate(opcode):
      symbol = self.D.getInfo(self.PC).tval
      if (opcode & 0x80):
        # It's an immediate unsigned 7 bit literal
        self.IMM(opcode & 0x7F, symbol = symbol)
      else:
        opname = self.Opcodes.OPCODENAME[opcode]
        if opname in self.Opcodes.LONGEROPCODES:
          # One of the immediate instructions
          opsize = self.Opcodes.LONGEROPCODES[opname]
          daddr = self.PC+1
          if opname == 'PCIMMS':
            val = self.ROM[daddr] + self.PC - 128
            if val < 0:
              symbol = ' '+symbol
            self.IMM(val, symbol = symbol)

          if opname == "IMMS":
            val = self.ROM[daddr] - 128
            if val < 0:
              symbol = ' '+symbol
            self.IMM(val, symbol = symbol)

          if opname == "IMMU":
            val = self.ROM[daddr] | (self.ROM[daddr+1] << 8)
            self.IMM(val, symbol = symbol)

          if opname == "IMMF":
            val = struct.unpack("<f", self.ROM[daddr:daddr+4])[0]
            if val < 0:
              symbol = ' '+symbol
            self.IMM(val, symbol = symbol)

      self.PC += opsize

    else:
      # Not immediate
      self.PC += 1

      opname = self.Opcodes.OPCODENAME[opcode]
      print(opname)
      if opname in self.OpMap:
        # Remap to a method name
        opname = self.OpMap[opname]

      getattr(self, opname)() # Call the method with this name

    if self.D.tagged(self.PC):
      tos = self.Stack.pop()
      tos = tos._replace(symbol=self.D.getTag(self.PC))
      self.Stack.push(tos)


  def ioWrite(self, x, y):
    self.Sim.ioWrite(x, y)

  def ioRead(self, x):
    self.Stack.push(self.Sim.ioRead(x))

  def memStore(self, val, addr):
    addri = int(round(addr.float))
    if addri < 0x100:
      # Write to scratch
      self.MemAddrSymbols[addri] = (addr.symbol, val.symbol, 'f')
      self.Scratch[addri:addri+4] = array.array('B', toFBytes(val.float))
      self.MemWriteList.append((addri, 4))
      return

    if (addri >= 0x1010) and (addri < 0x1020):
      # Write to packet TX
      self.MemAddrSymbols[addri] = (addr.symbol, val.symbol, 'f')
      self.TXPacket[addri:addri+4] = toFBytes(val.float)
      self.MemWriteList.append((addri, 4))
      return

    if (addri >= 0x2000) and (addri < 0x2400):
      # Write directly into program RAM
      self.MemAddrSymbols[addri] = (addr.symbol, val.symbol, 'f')
      addri = addri - 0x2000
      self.ROM[addri:addri+4] = toFBytes(val.float)
      self.MemWriteList.append((addri, 4))
      return

    raise VMCPUInvalidWrite('Write to invalid address')

  def memStoreB(self, val, addr):
    addri = int(round(addr.float))
    if addri < 0x100:
      # Write to scratch
      self.MemAddrSymbols[addri] = (addr.symbol, val.symbol, 'b')
      self.Scratch[addri] = int(round(val.float))
      self.MemWriteList.append((addri, 1))
      return

    if (addri >= 0x1010) and (addri < 0x1020):
      # Write to packet TX
      self.MemAddrSymbols[addri] = (addr.symbol, val.symbol, 'b')
      self.TXPacket[addri] = int(round(val.float))
      self.MemWriteList.append((addri, 1))
      return

    if (addri >= 0x2000) and (addri < 0x2400):
      # Write directly into program RAM
      self.MemAddrSymbols[addri] = (addr.symbol, val.symbol, 'b')
      addri = addri - 0x2000
      self.ROM[addri] = int(round(val.float))
      self.MemWriteList.append((addri, 1))
      return

    raise VMCPUInvalidWrite('Write to invalid address')

  def getMemAddrSymInfo(self, addri, suggestedvals=''):
    try:
      addrs, vals, vtype = self.MemAddrSymbols[addri]
    except KeyError:
      addrs = ''
      vals = suggestedvals
      vtype = ''

    return (addrs, vals, vtype)

  def concat(self, s1, s2):
    if s1 == None:
      s1 = ''
    if s2 == None:
      s1 = ' '
      s2 = ''

    return s1 + s2

  def memFetch(self, addr, suggestedvals=''):
    addri = int(round(addr.float))
    if addri < 0x0100:
      # Read from scratch
      addrs, vals, vtype = self.getMemAddrSymInfo(addri, suggestedvals=self.concat('@',addr.symbol))
      f = floatFromBytes(self.Scratch[addri:addri+4])
      return SEntry(f, vals)

    if (addri >= 0x1000) and (addri < 0x1010):
      # Read from packet RX
      addrs, vals, vtype = self.getMemAddrSymInfo(addri, suggestedvals=self.concat('@',addr.symbol))
      f = floatFromBytes(self.RXPacket[addri:addri+4])
      return SEntry(f, vals)

    if (addri >= 0x2000) and (addri < 0x2400):
      # Read directly from program RAM
      addrs, vals, vtype = self.getMemAddrSymInfo(addri, suggestedvals=self.concat('@',addr.symbol))
      addri = addri - 0x2000
      f = floatFromBytes(self.ROM[addri:addri+4])
      return SEntry(f, vals)

    raise VMCPUInvalidWrite('Write to invalid address')

  def memFetchB(self, addr):
    addri = int(round(addr.float))
    if addri < 0x0100:
      # Read from scratch
      addrs, vals, vtype = self.getMemAddrSymInfo(addri, suggestedvals=self.concat('@',addr.symbol))
      f = float(self.Scratch[addri])
      return SEntry(f, vals)

    if (addri >= 0x1000) and (addri < 0x1010):
      # Read from packet RX
      addrs, vals, vtype = self.getMemAddrSymInfo(addri, suggestedvals=self.concat('@',addr.symbol))
      f = float(self.RXPacket[addri])
      return SEntry(f, vals)

    if (addri >= 0x2000) and (addri < 0x2400):
      # Read directly from program RAM
      addrs, vals, vtype = self.getMemAddrSymInfo(addri, suggestedvals=self.concat('@',addr.symbol))
      addri = addri - 0x2000
      f = float(self.ROM[addri])
      return SEntry(f, vals)

    raise VMCPUInvalidWrite('Write to invalid address')

  """
  OPCODES START HERE
  """

  def DUP(self):
    # DUP   x -- x x
    x = self.Stack.pop()
    self.Stack.push(x)
    self.Stack.push(x)

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

  def ROT(self):
    # ROT    |a b c -- b c a   | Rotate top 3 values of stack around
    c = self.Stack.pop()
    b = self.Stack.pop()
    a = self.Stack.pop()
    self.Stack.push(b)
    self.Stack.push(c)
    self.Stack.push(a)

  def NROT(self):
    # NROT    |a b c -- c a b   | Rotate top 3 values of stack around
    c = self.Stack.pop()
    b = self.Stack.pop()
    a = self.Stack.pop()
    self.Stack.push(c)
    self.Stack.push(a)
    self.Stack.push(b)

  def PLUS(self):
    # +     x y -- (x+y)
    x, y = self.Stack.pop2()
    res = SEntry(x.float+y.float, f"{x.symbol}+{y.symbol}")
    self.Stack.push(res)

  def MINUS(self):
    # -     x y -- (x-y)
    x, y = self.Stack.pop2()
    res = SEntry(x.float-y.float, f"{x.symbol}-{y.symbol}")
    self.Stack.push(res)

  def TIMES(self):
    # *     x y -- (x*y)
    x, y = self.Stack.pop2()
    res = SEntry(x.float*y.float, f"({x.symbol})*({y.symbol})")
    self.Stack.push(res)    

  def DIV(self):
    # /     x y -- (x/y)
    x, y = self.Stack.pop2()
    res = SEntry(x.float/y.float, f"({x.symbol})/({y.symbol})")
    self.Stack.push(res)

  def POW(self):
    # POW   x y -- pow(x,y)
    x, y = self.Stack.pop2()
    res = SEntry(math.pow(x.float, y.float), f"POW({x.symbol}, {y.symbol})")
    self.Stack.push(res)

  def NEG(self):
    # NEG   x -- (-x)        : Invert sign of TOS.
    x = self.Stack.pop()
    res = SEntry(-x.float, f"-{x.symbol}")
    self.Stack.push(res)

  def REC(self):
    # REC   x -- (1/x)       : Reciprocal of TOS.
    x = self.Stack.pop()
    res = SEntry(1.0/x.float, f"(1.0/{x.symbol})")
    self.Stack.push(res)

  def TZ(self):
    # TZ    x -- 1|0         : Test Zero.  TOS = 1 if x  = 0, else 0
    x = self.Stack.pop()
    if x.float == 0:
      self.Stack.push(SEntry(1.0, f'({x.symbol}==0)'))
    else:
      self.Stack.push(SEntry(0.0, f'({x.symbol}==0)'))

  def TGT(self):
    # TGT   x y -- (x>y)     : Test Greater Than.  TOS = 1 if x  > y, else 0
    x, y = self.Stack.pop2()
    if x.float > y.float:
      self.Stack.push(SEntry(1.0, f"({x.symbol}>{y.symbol})"))
    else:
      self.Stack.push(SEntry(0.0, f"({x.symbol}>{y.symbol})"))

  def TLT(self):
    # TLT   x y -- (x<y)     : Test Less Than. TOS = 1 if x  < y, else 0
    x, y = self.Stack.pop2()
    if x.float < y.float:
      self.Stack.push(SEntry(1.0, f"({x.symbol}<{y.symbol})"))
    else:
      self.Stack.push(SEntry(0.0, f"({x.symbol}<{y.symbol})"))

  def TGE(self):
    # TGE   x y -- (x>=y)    : Test Greater or Equal.  TOS = 1 if x >= y, else 0
    x, y = self.Stack.pop2()
    if x.float >= y.float:
      self.Stack.push(SEntry(1.0, f"({x.symbol}>={y.symbol})"))
    else:
      self.Stack.push(SEntry(0.0, f"({x.symbol}>={y.symbol})"))

  def TLE(self):
    # TLE   x y -- (x<=y)    : Test Less or Equal. TOS = 1 if x <= y, else 0
    x, y = self.Stack.pop2()
    if x.float <= y.float:
      self.Stack.push(SEntry(1.0, f"({x.symbol}<={y.symbol})"))
    else:
      self.Stack.push(SEntry(0.0, f"({x.symbol}<={y.symbol})"))

  def TIN(self):
    # TIN   x -- 1|0         : Test Invalid Number. TOS = 1 if x is NaN or Inf
    x = self.Stack.pop()
    if math.isnan(x.float) or math.isinf(x.float):
      self.Stack.push(SEntry(1.0, f"TIN({x.symbol})"))
    else:
      self.Stack.push(SEntry(0.0, f"TIN({x.symbol})"))

  def OR(self):
    # OR    x y -- (x OR y) : Bitwise integer OR
    x, y = self.Stack.pop2()
    xi = int(round(x.float))
    yi = int(round(y.float))
    res = SEntry(xi|yi, f"({x.symbol}|{y.symbol})")
    self.Stack.push(res) # Push converts everything to a float32

  def AND(self):
    # AND   x y -- (x AND y) : Bitwise integer AND
    x, y = self.Stack.pop2()
    xi = int(round(x.float))
    yi = int(round(y.float))
    res = SEntry(xi & yi, f"({x.symbol}&{y.symbol})")
    self.Stack.push(res) # Push converts everything to a float32

  def XOR(self):
    # XOR   x y -- (x XOR y) : Bitwise integer XOR
    x, y = self.Stack.pop2()
    xi = int(round(x.float))
    yi = int(round(y.float))
    res = SEntry(xi ^ yi, f"({x.symbol}^{y.symbol})")
    self.Stack.push(res) # Push converts everything to a float32

  def BINV(self):
    # BINV  x   -- (~x)      : Bitwise Inverse. Treats x as an integer
    x = self.Stack.pop()
    xi = int(round(x.float))
    res = SEntry(~xi, f"~{x.symbol}")
    self.Stack.push(~x)

  def BNZ(self):
    # BNZ   x a --           : Branch to a if x != 0. 
    x, a = self.Stack.pop2()
    if x.float != 0:
      self.PC = int(round(a.float))

  def BZ(self):
    # BZ    x a --           : Branch to a if x == 0.
    x, a = self.Stack.pop2()
    if x.float == 0:
      self.PC = int(round(a.float))

  def BRA(self):
    # BRA   a   --           : Branch to a.
    a = self.Stack.pop()
    self.PC = int(round(a.float))

  def CALL(self):
    # CALL  x                : Execute word x.
    self.CallStack.push(SEntry(self.PC, f"{self.PC}"))  # PC should already be pointing to the next instruction
    a = self.Stack.pop()
    self.PC = int(round(a.float))

  def RET(self):
    # ;                      : Returns to calling word. Use at end of word only.
    a = self.CallStack.pop()
    self.PC = int(round(a.float))

  def EXIT(self):
    # EXIT                   : Returns to calling word. Use in middle of word only.
    a = self.CallStack.pop()
    self.PC = int(round(a.float))

  def WAIT(self):
    # WAIT                   : Sleep until the start of the next AC cycle.
    self.SysTime.waitTilNextACZero()

  def NOP(self):
    # NOP                    : Does nothing.
    pass

  def TOR(self):
    # TOR    |x  --            | Pop x and push to Call Stack (aka Return stack aka Control Stack)
    x = self.Stack.pop()
    self.CallStack.push(x)

  def FROMR(self):
    # FROMR  |-- x             | Pop from Call stack and push to ToS
    x = self.CallStack.pop()
    self.Stack.push(x)

  def COPYR(self):
    # COPYR  |-- x             | Push a copy of Call Stack ToS to ToS
    x = self.CallStack.read(0)
    self.Stack.push(x)

  def PCIMMS(self, imm, symbol=''):
    # PCIMMS # -- x          : Push PC + # onto the stack.
    x = self.PC + imm - 1    # PC has been pre-incremented, so subract 1
    if symbol=='':
      symbol = f"{x.float}"
    self.Stack.push(SEntry(x, symbol))

  def IMM(self, imm, symbol=''):
    if symbol=='':
      symbol = f"{imm.float}"
    print(imm)
    # IMM    # -- x          : Push an immediate value from (0..127) onto the stack.
    # IMMS   # -- x          : Push an immediate value from (-127 to 128) onto the stack.
    # IMMF   # -- x          : Push an immediate single-precision float (32-bit) onto the stack.
    self.Stack.push(SEntry(imm, symbol))

  def STORE(self):
    # STORE x y -- [y] = x   : Store x in slot y.
    x, y = self.Stack.pop2()
    self.memStore(x, y)

  def FETCH(self):
    # FETCH y -- [y]         : Fetch a value from slot y, put it on the stack.
    y = self.Stack.pop()
    self.Stack.push(self.memFetch(y))

  def STOREB(self):
    x, y = self.Stack.pop2()
    self.memStoreB(x, y)

  def FETCHB(self):
    y = self.Stack.pop()
    self.Stack.push(self.memFetchB(y))

  def TXP(self):
    # TXP     -- x           : Send a packet if possible. Return 1 if sent, 0 if dropped.
    res = SEntry(1, "SENT")
    self.Stack.push(res)

  def RXP(self):
    # RXP?    -- x           : Return 1 if a packet arrived, else zero. PacketData RX area is not modified until this is called.
    res = SEntry(1, "RECEIVED")
    self.Stack.push(res)    

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
    y = self.Stack.pop()
    self.ioReadTarget(y)

  def STOP(self):
    # STOP --              : STOPS CPU execution
    self.Stopped = True
    raise VMCPUStopped('STOP Executed')

  def FOR(self):
    """
      FOR is used to implement the beginning of a FOR loop. {} is used to
      represent the control stack

      FOR limit step index nextblockaddr -- {limit step index startaddr}      // Index is inside limits
       or
      FOR limit step index nextblockaddr -- ; PC = nextblockaddr    // Index is outside limits

      FOR copies the limit, step, and start of the loop variables onto the
      control stack, if the start index is inside the range, otherwise it
      branches to nextblockaddr. Either way, it consumes nextblockaddr.    

    """
    index, nextblockaddr = self.Stack.pop2()
    limit, step = self.Stack.pop2()
    nbai = int(round(nextblockaddr.float))
    nextblockaddr._replace(float=nbai)

    #print(limit, step, index, nextblockaddr)

    enterloop = True
    if step.float == 0.0:
      enterloop = False

    if step.float > 0.0:
      # Step is positive, index needs to be < limit
      if index.float >= limit.float:
        enterloop = False

    if step.float < 0.0:
      # Step is negative. Index needs to be > limit
      if index.float <= limit.float:
        enterloop = False

    if enterloop:
      self.CallStack.push(limit)
      self.CallStack.push(step)
      self.CallStack.push(index)
      self.CallStack.push(SEntry(self.PC, f"{self.PC}"))
    else:
      # Just branch to end of loop
      self.PC = nextblockaddr.float

  def ENDFOR(self):
    """
      ENDFOR is used to implement the end of a FOR loop. It adds the step to the
      index and checks against the limit. If the index is out of range, it removes
      the control information from the stack and goes to the next instruction.
      Otherwise, it branches back to startaddr

      ENDFOR {limit step index startaddr} -- {limit step index+step startaddr} ; PC = startaddr
       or
      ENDFOR {limit step index startaddr} -- {}; PC = PC+1
    """
    index, startaddr = self.CallStack.pop2()
    limit, step = self.CallStack.pop2()
    sai = int(round(startaddr.float))
    startaddr._replace(float=sai)

    i = index.float + step.float
    index = SEntry(i, f"{i}")
    leave = False
    if step.float > 0:
      if index.float >= limit.float:
        leave = True
    else:
      if index.float <= limit.float:
        leave = True

    if leave:
      # Do nothing, the next instruction will naturally execute
      pass
    else:
      self.CallStack.push(limit)
      self.CallStack.push(step)
      self.CallStack.push(index)
      self.CallStack.push(startaddr)
      self.PC = startaddr.float

  def INDEX(self):
    """
    Puts a FOR loop index on the ToS.
    INDEX x -- (Loop x's index)
    """
    loop = self.Stack.pop()
    posi = int(round(loop.float))
    posi = posi*4 + 1
    index = self.CallStack.read(posi)
    self.Stack.push(index)