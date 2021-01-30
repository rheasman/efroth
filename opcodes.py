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
    "TOC",
    "FROMC",
    "COPYC",
    "PCIMMS",
    "IMM",
    "IMMS",
    "IMMU",
    "IMMF",
    "STORE",
    "FETCH",
    "PS",
    "PF",
    "TXP",
    "RXP?",
    "IOR",
    "IOW",
    "IORT",
    "FOR",
    "ENDFOR"
  ]

  LONGEROPCODES = {
    "PCIMMS" : 2,
    "IMMS"   : 2,
    "IMMU"   : 3,
    "IMMF"   : 5
  }
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



if __name__ == '__main__':
  O = OpCodes()
  print(O.OPCODELIST)
  print(len(O.OPCODELIST))
  print(O.OPCODENUM)
  print(O.OPCODENAME)
