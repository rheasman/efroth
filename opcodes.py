import collections

class OpCodes:
  OPCODELIST = [
    "NOP",
    "DUP",
    "DROP",
    "OVER",
    "SWAP",
    "PICK",
    "+",
    "-",
    "*",
    "/",
    "POW",
    "NEG",
    "REC",
    "TZ",
    "TGT",
    "TLT",
    "TGE",
    "TLE",
    "TIN",
    "OR",
    "AND",
    "XOR",
    "BINV",
    "BNZ",
    "BZ",
    "BRA",
    "CALL",
    ";",
    "WAIT",
    "NOP",
    "TOR",
    "FROMR",
    "COPYR",
    "PCIMMS",
    "IMM",
    "IMMS",
    "IMMU",
    "IMMF",
    "!",
    "@",
    "!B",
    "@B",
    "TXP",
    "RXP?",
    "IOR",
    "IOW",
    "IORT",
    "FOR",
    "ENDFOR",
    "STOP",
    "INDEX"
  ]

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
