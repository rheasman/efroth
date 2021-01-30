#!/usr/bin/env python3
import json, sys, opcodes

Ops = opcodes.OpCodes()

def json_import(filename):
  with open(filename, 'r') as infile:
    res = json.load(infile)
    
  return res

def main(filename):
  data = json_import(filename)
  #print(data)
  AddrToSource = data['AddrToSource']
  Words = data['Words']
  #print(Words)
  wordsbyaddr = {}
  for word in Words:
    num, addr = Words[word]
    wordsbyaddr[addr] = (word, num)

  membytes = [x[1][-1] for x in AddrToSource.items()]

  addr = 0
  indent = 0
  while addr < len(membytes):
    oname = ''
    (otype, tpos, tlinepos, tcolpos, tval, tbyte) = AddrToSource[str(addr)]
    olen = 1
    if (otype == 0):
      oname = Ops.OPCODENAME[tbyte]
      if oname in Ops.LONGEROPCODES:
        olen = Ops.LONGEROPCODES[oname]
      if oname in Ops.OUTDENT:
        indent -= 1

    if addr in wordsbyaddr:
      print(f"\n{wordsbyaddr[addr][0]}:")
    
    print("  %04X" % addr, end='')
    print(" %02X" % (membytes[addr]), end='')
    indentstr = "  " * indent
    print(indentstr, end='')
    for i in range(1, olen):
      print(" %02X" % (membytes[addr+i]), end='')

    if otype == 0:
      if (olen > 1):
        print(" %s // %s " % (oname, tval))
      else:
        print(" %s" % (oname))
    else:
      print(" %s" % (tval))

    if (oname in Ops.INDENT):
      indent += 1

    addr += olen


if __name__ == '__main__':
  main(sys.argv[1])