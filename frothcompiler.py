import array, collections
import opcodes, ioconsts
import struct, sys, json

class FrothCompiler:      
  Opcodes = opcodes.OpCodes()
  IO = ioconsts.IOConsts()
  WordCnt = 0
  Words = collections.OrderedDict()
  Globals = collections.OrderedDict()
  GlobalLastAddr = 0
  WordList = []
  WordStackUse = {}
  Labels = {}
  Addr = 0
  Fixups = collections.deque()
  ROM = array.array("B")
  StackUse = (0,0)

  StackIdList = []       # Names for positions in the current stack
  StackIdAfterList = []  # Names for positions in the stack after this word has been called
  DeferredCopies = [] # Stack items that will need to be copied before the next opcode

  # Struct to map ROM address ranges to symbols
  DebugInfo = {}
  AddrToSource = {}
  Tags = {}
  T_OPCODE = 0
  T_VAL = 1  


  def __init__(self, cocoparent):
    self.Parser = cocoparent

  def updateStackUse(self, maindiff, retdiff):
    #print(maindiff, retdiff)
    self.StackUse = (self.StackUse[0] + maindiff, self.StackUse[1] + retdiff)
    while maindiff > 0:
      self.StackIdList.append("-")
      maindiff -= 1

    while len(self.StackIdList) and (maindiff < 0):
      self.StackIdList.pop()
      maindiff += 1


  def emit(self, op, otype, newop, comment=''):
    #print("StackIDs:", self.StackIdList)
    if len(self.DeferredCopies):
      self.emitCopies()

    print("%5d" % self.Addr, "%6s" % op, "  ", comment)
    if op in self.Opcodes.OPCODESET:
      self.updateStackUse(*self.Opcodes.OPNETSTACK[op])
      self.ROM.append(self.Opcodes.OPCODENUM[op])
    else:
      self.ROM.append(op)

    if (op == ';') or (op == 'EXIT'):
      print("Stack delta:", self.StackUse)
      self.checkWordStacks()
      currentword = self.WordList[-1]
      self.WordStackUse[currentword] = self.StackUse

    self.AddrToSource[int(self.Addr)] = (newop, otype, self.Parser.token.pos, self.Parser.token.line, self.Parser.token.col, self.Parser.token.val, self.ROM[-1])
    self.Addr += 1

  def emitCopies(self):
    """
    If there are values to be copied to the top of the stack, do it now
    """
    copies = list(self.DeferredCopies)
    self.DeferredCopies = []
    while len(copies):
      print(repr(copies))
      if len(copies) == 1:
        # Just one copy
        copy = copies.pop(0)
        copyindex = len(self.StackIdList) - self.StackIdList.index(copy)
        self.emit(self.Opcodes.encodeCopy(copyindex, 0), self.T_OPCODE, 1, f"// Copy {copy}")
        self.StackIdList.append("-")

      if len(copies) >= 2:
        # Copy two items
        copy1 = copies.pop(0)
        copy2 = copies.pop(0)
        copyindex1 = len(self.StackIdList) - self.StackIdList.index(copy1)
        copyindex2 = len(self.StackIdList) - self.StackIdList.index(copy2)
        self.emit(self.Opcodes.encodeCopy(copyindex1, copyindex2), self.T_OPCODE, 1, f"// Copy {copy1}, {copy2}")          
        self.StackIdList.append("-")
        self.StackIdList.append("-")


  def checkWordStacks(self):
    currentword = self.WordList[-1]
    if currentword in self.WordStackUse:
      # Check that stack use matches at all exits
      u = self.WordStackUse[currentword]
      if self.StackUse != u:
        self.Parser.SemErr( f"Stack usage must be the same at all word exits. Previous = {u}, current = {self.StackUse}." )

  def addWord(self, wordstr):
    if wordstr not in self.Words:
      self.StackUse = (0,0)
      self.Words[wordstr] = (self.WordCnt, self.Addr)
      self.WordList.append(wordstr)
      print(": %s" % wordstr)
      self.WordCnt += 1
      return wordstr
    else:
      self.Parser.SemErr(f"'{wordstr}' already defined: ")

  def addGlobal(self, gstr):
   if gstr not in self.Globals:
     self.Globals[gstr] = self.GlobalLastAddr
     print("GLOBAL: %s" % gstr)
     self.GlobalLastAddr += 4
   else:
     self.Parser.SemErr(f"'{gstr}' already defined: ")       

  def addLabel(self, label):
   labelname = self.WordList[-1] + '::' + label
   if labelname in self.Labels:
     self.Parser.SemErr("Label already defined: " + labelname)
   else:
     self.Labels[labelname] = self.Addr
     print("{%s}" % labelname)

  def addTag(self, tag):
   self.Tags[self.Addr] = tag
   print("%5d" % self.Addr, "<%s>" % tag)

   # Update stack ids if necessary
   if len(self.StackIdList):
     self.StackIdList.pop()
     self.StackIdList.append(tag)

  def emitWord(self, wordstr, comment=''):
    if wordstr in self.Opcodes.OPCODESET:
      # It's an opcode
      self.emit(wordstr, self.T_OPCODE, 1, comment=comment)
      return
    
    if wordstr in self.IO.IODICT:
      # It's a defined IO constant
      self.emitVal(self.IO.IOCONSTVAL[wordstr], comment="// %s: %d" % (wordstr, self.IO.IOCONSTVAL[wordstr]))
      diffm, diffr = (1, 0)

      return

    if wordstr in self.Words:
      waddr = self.Words[wordstr][1]
      self.emitVal(waddr, comment="// %5d %s" % (waddr, wordstr))
      self.emit("CALL", self.T_OPCODE, 1)
      #print("Stack use before:", self.StackUse)
      (m, r) = self.WordStackUse[wordstr]
      self.StackUse = (self.StackUse[0]+m, self.StackUse[1]+r)
      #print("Stack use after:", self.StackUse)

      return

    # Maybe it's a label
    labelname = self.WordList[-1] + '::' + wordstr
    if labelname in self.Labels:
      laddr = self.Labels[labelname]
      self.emitVal(laddr, comment = "// %s" % labelname)
      return

    # Maybe it's a stack id
    if wordstr in self.StackIdList:
      self.DeferredCopies.append(wordstr)
      return

    # Maybe it's a global
    if wordstr in self.Globals:
      val = self.Globals[wordstr]
      self.emitVal(val, comment = "// %s (%d)" % (wordstr, val))
      return

    self.Parser.SemErr(f"Didn't know what to do with: '{wordstr}'. It's not an opcode, word, known constant, or label." )  

  def floatToBytes(self, floatval):
   bitpattern = struct.pack("<f", float(floatval))
   return struct.unpack("BBBB", bitpattern)

  def emitFloat(self, floatval, comment=''):
    floatval = float(floatval)
    bytes = self.floatToBytes(floatval)
    self.emit("IMMF", self.T_OPCODE, 1);
    self.emit(bytes[0], self.T_VAL, 0, comment = "// %02X (float: %8f)" % (bytes[0], floatval))
    self.emit(bytes[1], self.T_VAL, 0, comment = "// %02X" % (bytes[1]))
    self.emit(bytes[2], self.T_VAL, 0, comment = "// %02X" % (bytes[2]))
    self.emit(bytes[3], self.T_VAL, 0, comment = "// %02X" % (bytes[3]))

  def emitAddr(self, addr, addfixup=False, comment=''):
    if (addr >=0) and (addr < 65536):
      # 16 bit unsigned immediate
      self.emit('IMMU', self.T_OPCODE, 1)
      if addfixup:
        self.Fixups.append(self.Addr)
      self.emit(addr & 0xFF, self.T_VAL, 0,  comment=comment)
      self.emit((addr >> 8) & 0xFF, self.T_VAL, 0, comment=comment)
      return

  def fixupAddr(self, addr):
    d = list(self.AddrToSource[addr])
    d[-1] = self.ROM[addr]
    self.AddrToSource[addr] = tuple(d)

  def doFixup(self, tofix, addr):
    print(f"Fixup {tofix} to {addr}")

    self.ROM[tofix] = addr & 0xFF
    self.fixupAddr(tofix) 

    self.ROM[tofix+1] = (addr >> 8) & 0xFF
    self.fixupAddr(tofix) 


  def emitVal(self, val, comment=''):
    val = float(val)
    intval = int(val)
    fracval = val % 1

    # It's a float
    if (fracval != 0):
      self.emitFloat(val)
      return

    if (intval >= 0) and (intval < 128):
      # 7-bit immediate
      # comment = "// %s %s" % (intval & 0x7F, comment)
      self.emit(0x80 | intval, self.T_VAL, 1, comment=comment)
      self.updateStackUse(1,0)
      return

    if (intval >= -128) and (intval < 128):
      # 8-bit immediate
      self.emit('IMMS', self.T_OPCODE, 1)
      self.emit(intval, self.T_VAL, 0, comment=comment)
      return

    offset = intval - self.Addr
    if (offset >= -128) and (offset < 128):
      # PC-relative number
      self.emit('PCIMMS', self.T_OPCODE, 1)
      self.emit(offset, self.T_VAL, 0, comment=comment)
      return

    if (intval >=0) and (intval < 65536):
      # 16 bit unsigned immediate
      self.emit('IMMU', self.T_OPCODE, 1)
      self.emit(intval & 0xFF, self.T_VAL, 0, comment=comment)
      self.emit((intval >> 8) & 0xFF, self.T_VAL, 0, comment=comment)
      return

    # Fine, no efficient way to encode the value
    self.emitFloat(val, comment=comment)

  def checkWords(self):
   if "RunShot" not in self.Words:
     self.Parser.SemErr( "The word 'RunShot' must be defined." )
   if "Idle" not in self.Words:
     self.Parser.SemErr( "The word 'Idle' must be defined." )
   if "Halt" not in self.Words:
     self.Parser.SemErr( "The word 'Halt' must be defined." )

  def checkPathsEqual(self, p1, p2):
   if (p1[0] != p2[0]) or (p1[1] != p2[1]):
     self.Parser.SemErr( f"Both paths through a conditional should have the same effect on stack sizes, {p1} vs {p2}" )

  def writeResults(self, inputfile, outputfile):
    #print(self.AddrToSource)
    #print(self.Words)
    debuginfo = {
      'AddrToSource' : self.AddrToSource,
      'Words' : self.Words,
      'Tags' : self.Tags
    }

    #print("Object code:")
    #bytes = [format(x, "02X") for x in self.ROM]
    #print("  ", ",".join(bytes))
    #print()
    addr_shot = self.Words['RunShot'][1]
    addr_idle = self.Words['Idle'][1]
    addr_halted = self.Words['Halt'][1]
    with open(outputfile+".bin", "wb") as f:
      data = struct.pack(f"<4sHHHHHHH{len(self.ROM)}s", b"EFVM", 
        0,             # Version
        self.MaxVol,
        self.MaxSec,
        0x12,          # Start of ROM
        addr_shot,
        addr_idle,
        addr_halted,
        self.ROM.tobytes()
      )
      f.write(data)
    
    with open(inputfile,'r') as infile:
      debuginfo["Source"] = infile.read()

    with open(outputfile+".debug", 'w') as outfile:
      json.dump(debuginfo, outfile, indent=2)
    
  def startFor(self):
    self.emitAddr(0, addfixup=True)
    self.emitWord("FOR")

  def endFor(self, addr):
    self.emitWord("ENDFOR", comment=f"// FOR at {addr}.")
    self.doFixup(self.Fixups.pop(), self.Addr)

  def addStackBeforeId(self, id):
   self.StackIdList.append(id)
   #print(self.StackIdList)

  def addStackAfterId(self, id):
   self.StackIdAfterList.append(id)
   #print(self.StackIdAfterList)

  def clearStackIds(self):
    self.StackIdList = []
    self.StackIdAfterList = []

  def discardStackId(self, id):
   pass
