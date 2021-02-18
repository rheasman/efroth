import collections

class OpCodes:
  OPCODEDICT = {
    "DUP"    : ( 1, 0),  # Numbers are the net effect on the main stack and the return stack
    "DROP"   : (-1, 0),
    "OVER"   : ( 1, 0),
    "SWAP"   : ( 0, 0),
    "COPY"   : ( 1, 0),
    "ROT"    : ( 0, 0),
    "NROT"   : ( 0, 0),
    "+"      : (-1, 0),
    "-"      : (-1, 0),
    "*"      : (-1, 0),
    "/"      : (-1, 0),
    "POW"    : (-1, 0),
    "NEG"    : ( 0, 0),
    "REC"    : ( 0, 0),
    "TZ"     : ( 0, 0),
    "TGT"    : (-1, 0),
    "TLT"    : (-1, 0),
    "TGE"    : (-1, 0),
    "TLE"    : (-1, 0),
    "TIN"    : ( 0, 0),
    "OR"     : (-1, 0),
    "AND"    : (-1, 0),
    "XOR"    : (-1, 0),
    "BINV"   : ( 0, 0),
    "BNZ"    : (-2, 0),
    "BZ"     : (-2, 0),
    "BRA"    : (-1, 0),
    "CALL"   : (-1, 1),
    ";"      : ( 0,-1),
    "EXIT"   : ( 0,-1),
    "WAIT"   : ( 0, 0),
    "NOP"    : ( 0, 0),
    "TOR"    : (-1, 1),
    "FROMR"  : ( 1,-1),
    "COPYR"  : ( 1, 0),
    "PCIMMS" : ( 1, 0),
    "IMM"    : ( 1, 0),
    "IMMS"   : ( 1, 0),
    "IMMU"   : ( 1, 0),
    "IMMF"   : ( 1, 0),
    "!"      : (-2, 0),
    "@"      : ( 0, 0),
    "!B"     : (-2, 0),
    "@B"     : ( 0, 0),
    "TXP"    : ( 1, 0),
    "RXP?"   : ( 1, 0),

    "IOR"    : ( 0, 0),
    "IOW"    : (-2, 0),
    "IORT"   : ( 0, 0),
    "FOR"    : (-4, 4),
    # ENDFOR is special. If you get past it, it removes things from the return stack. If it branches back, it doesn't. So, ignore the branch back phase.
    "ENDFOR" : ( 0,-4),
    "STOP"   : ( 0, 0),
    "INDEX"  : ( 1, 0)
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
