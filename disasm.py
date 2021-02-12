#!/usr/bin/env python3
import array, json, sys, opcodes
import collections, struct



Ops = opcodes.OpCodes()

def json_import(filename):
  with open(filename, 'r') as infile:
    res = json.load(infile)
    
  return res


AddrInfo = collections.namedtuple('AddrInfo', "newins, otype, tpos, tlinepos, tcolpos, tval, tbyte, oname, olen")
def getInfo(addrmap, addr):
  oname = ''
  (newins, otype, tpos, tlinepos, tcolpos, tval, tbyte) = addrmap[addr]
  olen = 1
  if (otype == 0):
    oname = Ops.OPCODENAME[tbyte]
    if oname in Ops.LONGEROPCODES:
      olen = Ops.LONGEROPCODES[oname]

  return AddrInfo(newins, otype, tpos, tlinepos, tcolpos, tval, tbyte, oname, olen)


"""
Starting to figure this out.

Want the source line as a field
Want memory dump hex characters as a field. Perhaps brackets around each opcode?
Want opcodes and number values as a field.
Need to encode the start of each opcode.

Output memory dump 

"""

class DebugDis:
  AddrInfo = collections.namedtuple('AddrInfo', "newins, otype, tpos, tlinepos, tcolpos, tval, tbyte")

  def __init__(self, debugfile):
    self.Data = self.json_import(debugfile)
    atos = self.Data['AddrToSource']
    self.AddrToSource = {}
    for i in atos:
      self.AddrToSource[int(i)] = atos[i]

    self.Tags = {}
    atot = self.Data['Tags']
    for i in atot:
      self.Tags[int(i)] = atot[i]

    self.Words = self.Data['Words']
    self.SourceLines = self.Data['Source'].splitlines()
    self.WordsByAddr = {}
    for word in self.Words:
      num, addr = self.Words[word]
      self.WordsByAddr[int(addr)] = (word, num)

    self.PrettyAddr = {}
    lastaddr = 0
    lastword = ''
    #print(self.Words)
    for addr in self.AddrToSource.keys():
      anum = int(addr)

    self.MemBytes = array.array('B', [x[1][-1] for x in self.AddrToSource.items()])

    self.MemToSourceLine = {}
    self.SourceLineToMem = {}
    for addr, i in reversed(list(enumerate(self.AddrToSource.items()))):
      ln = i[1][3]
      self.MemToSourceLine[addr] = ln
      self.SourceLineToMem[ln] = addr

  def getSourceLineForAddr(self, addr):
    return self.MemToSourceLine[addr]

  def getAddrForSourceLine(self, sl):
    while (sl <= len(self.SourceLines)) and (sl not in self.SourceLineToMem):
      sl += 1

    return self.SourceLineToMem[sl]

  def getInfo(self, addr):
    oname = ''
    (newins, otype, tpos, tlinepos, tcolpos, tval, tbyte) = self.AddrToSource[addr]
    olen = 1
    if (otype == 0):
      oname = Ops.OPCODENAME[tbyte]
      if oname in Ops.LONGEROPCODES:
        olen = Ops.LONGEROPCODES[oname]

    return AddrInfo(newins, otype, tpos, tlinepos, tcolpos, tval, tbyte, oname, olen)

  def tagged(self, addr):
    return addr in self.Tags

  def getTag(self, addr):
    return self.Tags[addr]

  def json_import(self, filename):
    with open(filename, 'r') as infile:
      res = json.load(infile)
      
    return res

  def getImmediateValue(self, addr):
    """
    Assuming the given address is the first byte of an immediate, return the value
    """

    op = self.MemBytes[addr]
    if op & 0x80:
      return self.MemBytes[addr] & 0x7F

    opname = Ops.OPCODENAME[op]
    if opname == "IMMS":
      return (self.MemBytes[addr+1]) - 128

    if opname == "IMMS":
      return (self.MemBytes[addr+1]) - 128

    if opname == "IMMU":
      return self.MemBytes[addr+1] + (256*self.MemBytes[addr+2])

    if opname == "IMMF":
      return struct.unpack("<f", self.MemBytes[addr+1:addr+1+4])[0]

    # If we get here then there is an error
    fail

  def getOpcode(self, addr):
    """
    Returns a tuple:
      (address, opcodebytes, valueifnotnone, disassembled opcode)
    """
    info = getInfo(self.AddrToSource, addr)
    if info.newins:
      line = []
      line.append(addr)

      oplen = Ops.opcodeLen(self.MemBytes[addr])
      line.append(self.MemBytes[addr:addr+oplen].tolist())
      if Ops.isImmediate(self.MemBytes[addr]):
        line.append(self.getImmediateValue(addr))
        line.append(info.tval)
      else: # OPCODE
        line.append(None)
        line.append(info.oname)

      return line

    return None

  def dumpOpcodes(self):
    result = []
    addr = 0
    while addr < len(self.MemBytes):
      o = self.getOpcode(addr)
      result.append(o)
      addr += len(o[1])

    return result


def disasm(filename):
  data = json_import(filename)
  #print(data)
  AddrToSource = data['AddrToSource']
  Words = data['Words']
  SourceLines = data['Source'].splitlines()
  #print(Words)
  wordsbyaddr = {}
  for word in Words:
    num, addr = Words[word]
    wordsbyaddr[addr] = (word, num)

  membytes = [x[1][-1] for x in AddrToSource.items()]

  addr = 0
  indent = 0
  lastoname = ''
  lastline = 0
  while addr < (len(membytes)):

    info = getInfo(AddrToSource, addr)    

    #while info.tlinepos > lastline:
    #  print("%4d %s" % ((lastline+1), SourceLines[lastline]))
    #  lastline += 1

    #if addr in wordsbyaddr:
    #  print(f"\n{wordsbyaddr[addr][0]}:")

    if info.oname:
      lastoname = info.oname

    spacer = ' '*10
    if info.newins:
      print("%s%04X" % (spacer, addr), end='')
      
    print(" %02X" % (membytes[addr]), end='')

    if info.newins:
      if info.otype == 0:
        print(" %s" % (info.oname), end='')
      else:
        print(" %s" % (info.tval), end='')

    addr += 1
    if (addr < len(membytes)) and (getInfo(AddrToSource, addr).newins):
      if lastoname == "IMMF":
        print(" // %s" % info.tval, end='')
      lastoname = ''
      print()

  print()


def main(filename):
  D = DebugDis(filename)
  addr = 0
  while addr < len(D.MemBytes):
    o = D.getOpcode(addr)
    print(o)
    addr += len(o[1])

if __name__ == '__main__':
  main(sys.argv[1])