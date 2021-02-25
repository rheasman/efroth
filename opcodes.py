import collections

StackInfo = collections.namedtuple("StackInfo", "mbefore mafter rbefore rafter special")
class OpCodes:
  OPCODEDICT = {
    
    # Initially stored the net effect on the main stack and the return stack,
    # but I found out that I needed more info than that So now, store proper
    # stack descriptions. If special is nonzero, then it needs special
    # handling. Special will be a unique integer in case I need to index
    # different special cases.

    "DUP"    : StackInfo('a',      'a a',    '',       '', 0),  
    "DROP"   : StackInfo('a',      '',       '',       '', 0),
    "OVER"   : StackInfo('a b',    'a b a',  '',       '', 0),
    "SWAP"   : StackInfo('a b',    'b a',    '',       '', 0),  
    "COPY"   : StackInfo('',       '',       '',       '', 1),  # Copy has a variable effect on the stack, so mark it special
    "ROT"    : StackInfo('a b c',  'b c a',  '',       '', 0),  # Front goes to back
    "NROT"   : StackInfo('a b c',  'c a b',  '',       '', 0),  # Back goes to front
    "+"      : StackInfo('a b',    'c',      '',       '', 0),
    "-"      : StackInfo('a b',    'c',      '',       '', 0),
    "*"      : StackInfo('a b',    'c',      '',       '', 0),
    "/"      : StackInfo('a b',    'c',      '',       '', 0),
    "POW"    : StackInfo('a b',    'c',      '',       '', 0),
    "NEG"    : StackInfo('a',      'b',      '',       '', 0),
    "REC"    : StackInfo('a',      'b',      '',       '', 0),
    "TZ"     : StackInfo('a',      'b',      '',       '', 0),
    "TGT"    : StackInfo('a',      'b',      '',       '', 0),
    "TLT"    : StackInfo('a',      'b',      '',       '', 0),
    "TGE"    : StackInfo('a',      'b',      '',       '', 0),
    "TLE"    : StackInfo('a',      'b',      '',       '', 0),
    "TIN"    : StackInfo('a',      'b',      '',       '', 0),
    "OR"     : StackInfo('a b',    'c',      '',       '', 0),
    "AND"    : StackInfo('a b',    'c',      '',       '', 0),
    "XOR"    : StackInfo('a b',    'c',      '',       '', 0),
    "BINV"   : StackInfo('a',      'b',      '',       '', 0),
    "BNZ"    : StackInfo('a b',     '',      '',       '', 0),
    "BZ"     : StackInfo('a b',     '',      '',       '', 0),
    "BRA"    : StackInfo('a',      '',       '',       '', 0),
    "CALL"   : StackInfo('a',      '',       '',      'a', 0),
    ";"      : StackInfo('',       '',       'a',      '', 0),
    "EXIT"   : StackInfo('',       '',       'a',      '', 0),
    "WAIT"   : StackInfo('',       '',       '',       '', 0),
    "NOP"    : StackInfo('',       '',       '',       '', 0),
    "TOR"    : StackInfo('a',      '',       '',      'a', 0),
    "FROMR"  : StackInfo('',       'a',      'a',      '', 0),
    "COPYR"  : StackInfo('',       'a',      'a',      '', 0),
    "PCIMMS" : StackInfo('',       'a',      '',       '', 0),
    "IMM"    : StackInfo('',       'a',      '',       '', 0),
    "IMMS"   : StackInfo('',       'a',      '',       '', 0),
    "IMMU"   : StackInfo('',       'a',      '',       '', 0),
    "IMMF"   : StackInfo('',       'a',      '',       '', 0),
    "!"      : StackInfo('a b',    '',       '',       '', 0),
    "@"      : StackInfo('a',      'b',      '',       '', 0),
    "!B"     : StackInfo('a b',    '',       '',       '', 0),
    "@B"     : StackInfo('a',      'b',      '',       '', 0),
    "TXP"    : StackInfo('',       'a',      '',       '', 0),
    "RXP?"   : StackInfo('',       'a',      '',       '', 0),

    "IOR"    : StackInfo('a',      'b',      '',       '', 0),
    "IOW"    : StackInfo('a b',    '',       '',       '', 0),
    "IORT"   : StackInfo('a',      'b',      '',       '', 0),

    "FOR"    : StackInfo('a b c d','',       '','a b c e', 0),
    
    # ENDFOR is special. If you get past it, it removes things from the return
    # stack. If it branches back, it doesn't. So, ignore the branch back
    # phase. FOR and ENDFOR make a single opcode that has predictable
    # behaviour on the stack once both have been executed.
    
    "ENDFOR" : StackInfo('',       '',       'a b c d','', 0),


    "STOP"   : StackInfo('',       '',       '',       '', 0),
    "INDEX"  : StackInfo('',       'a',      '',       '', 2)  # Another special case
  }

  OPCODELIST = [x for x in OPCODEDICT.keys()]
  LONGEROPCODES = {
    "PCIMMS" : 2,
    "IMMS"   : 2,
    "IMMU"   : 3,
    "IMMF"   : 5
  }

  OPCODELEN = {}
  OPCODESET = set(OPCODELIST)
  OPCODENUM = collections.OrderedDict()
  OPCODENAME = collections.OrderedDict()
  for num, op in enumerate(OPCODELIST):
    OPCODENUM[op] = num
    OPCODENAME[num] = op

  OPNETSTACK = {}

  def countitems(x):
    # Count non-empty items
    cnt = 0
    for i in x:
      if len(i) > 0:
        cnt += 1

    return cnt

  for i in OPCODEDICT.keys():
    info = OPCODEDICT[i]
    mbefore = countitems(info.mbefore.split(" "))
    mafter  = countitems(info.mafter.split(" "))
    rbefore = countitems(info.rbefore.split(" "))
    rafter  = countitems(info.rafter.split(" "))
    OPNETSTACK[i] = (mafter - mbefore, rafter - rbefore)

  INDENT = set([
    "FOR",
    "IF",
    "ELSE"
    ])
  OUTDENT = set([
    "ENDFOR",
    "ELSE",
    "ENDIF"
    ])

  def isImmediate(self, opcode):
    if opcode & 0x80:
      return True

    if self.opcodeLen(opcode) > 1:
      return True

    return False

  def isCopy(self, opcode):
    if opcode & 0x40:
      return True

    return False

  def getCopyOffsets(self, opcode):
    opcode = opcode & 0x3F
    return (opcode & 0x3, (opcode >> 3) & 0x3)

  def encodeCopy(self, pos1, pos2):
    """
    Encode up to two copies, positions 0 - 7.
    0 means no copy. 1 means copy 0, 2 means copy 1, etc.
    First copy is LSB. Stack positions don't update
    until after both copies.
    """
    if pos1 > 7:
      raise ValueError( "pos1 should be 0 - 7" )

    if pos2 > 7:
      raise ValueError( "pos2 should be 0 - 7" )

    return (pos1 & 0x7) | ((pos2 & 0x7) << 3) | 0x40


  def opcodeLen(self, num):
    if num & 0x80:
      return 1

    name = self.OPCODENAME[num]
    return self.opNameLen(name)

  def opNameLen(self, name):
    # Length of opcode, in bytes
    if name in self.LONGEROPCODES:
      return self.LONGEROPCODES[name]

    return 1


if __name__ == '__main__':
  O = OpCodes()
  print(O.OPCODELIST)
  print(len(O.OPCODELIST))
  print(O.OPCODENUM)
  print(O.OPCODENAME)
