#-------------------------------------------------------------------------
#Parser.py -- ATG file parser
#Compiler Generator Coco/R,
#Copyright (c) 1990, 2004 Hanspeter Moessenboeck, University of Linz
#extended by M. Loeberbauer & A. Woess, Univ. of Linz
#ported from Java to Python by Ronald Longo
#
#This program is free software; you can redistribute it and/or modify it
#under the terms of the GNU General Public License as published by the
#Free Software Foundation; either version 2, or (at your option) any
#later version.
#
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
#for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program; if not, write to the Free Software Foundation, Inc.,
#59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
#As an exception, it is allowed to write an extension of Coco/R that is
#used as a plugin in non-free software.
#
#If not otherwise stated, any source code generated by Coco/R (other than
#Coco/R itself) does not fall under the GNU General Public License.
#-------------------------------------------------------------------------*/

import array, collections
import opcodes, ioconsts
import struct, sys, json


import sys

from Scanner import Token
from Scanner import Scanner
from Scanner import Position

class ErrorRec( object ):
   def __init__( self, l, c, s ):
      self.line   = l
      self.col    = c
      self.num    = 0
      self.str    = s


class Errors( object ):
   errMsgFormat = "file %(file)s : (%(line)d, %(col)d) %(text)s\n"
   eof          = False
   count        = 0         # number of errors detected
   fileName     = ''
   listName     = ''
   mergeErrors  = False
   mergedList   = None      # PrintWriter
   errors       = [ ]
   minErrDist   = 2
   errDist      = minErrDist
      # A function with prototype: f( errorNum=None ) where errorNum is a
      # predefined error number.  f returns a tuple, ( line, column, message )
      # such that line and column refer to the location in the
      # source file most recently parsed.  message is the error
      # message corresponging to errorNum.

   @staticmethod
   def Init( fn, dir, merge, getParsingPos, errorMessages ):
      Errors.theErrors = [ ]
      Errors.getParsingPos = getParsingPos
      Errors.errorMessages = errorMessages
      Errors.fileName = fn
      listName = dir + 'listing.txt'
      Errors.listName = listName
      Errors.mergeErrors = merge
      if Errors.mergeErrors:
         try:
            Errors.mergedList = open( listName, 'w' )
         except IOError:
            raise RuntimeError( '-- Compiler Error: could not open ' + listName )

   @staticmethod
   def storeError( line, col, s ):
      if Errors.mergeErrors:
         Errors.errors.append( ErrorRec( line, col, s ) )
      else:
         Errors.printMsg( Errors.fileName, line, col, s )

   @staticmethod
   def SynErr( errNum, errPos=None ):
      line,col = errPos if errPos else Errors.getParsingPos( )
      msg = Errors.errorMessages[ errNum ]
      Errors.storeError( line, col, msg )
      Errors.count += 1

   @staticmethod
   def SemErr( errMsg, errPos=None ):
      line,col = errPos if errPos else Errors.getParsingPos( )
      Errors.storeError( line, col, errMsg )
      Errors.count += 1

   @staticmethod
   def Warn( errMsg, errPos=None ):
      line,col = errPos if errPos else Errors.getParsingPos( )
      Errors.storeError( line, col, errMsg )

   @staticmethod
   def Exception( errMsg ):
      print(errMsg)
      sys.exit( 1 )

   @staticmethod
   def printMsg( fileName, line, column, msg ):
      vals = { 'file':fileName, 'line':line, 'col':column, 'text':msg }
      sys.stdout.write( Errors.errMsgFormat % vals )

   @staticmethod
   def display( s, e ):
      Errors.mergedList.write('**** ')
      for c in range( 1, e.col ):
         if s[c-1] == '\t':
            Errors.mergedList.write( '\t' )
         else:
            Errors.mergedList.write( ' ' )
      Errors.mergedList.write( '^ ' + e.str + '\n')

   @staticmethod
   def Summarize( sourceBuffer ):
      if Errors.mergeErrors and Errors.count:
        errs = list(Errors.errors)
        for (srcLineNum, srcLineStr) in enumerate(iter(sourceBuffer), start=1):
          Errors.mergedList.write( '%4d %s\n' % (srcLineNum, srcLineStr.rstrip()) )
          while errs and (errs[0].line == srcLineNum):
            err = errs.pop(0)
            Errors.display( srcLineStr, err )

        if errs:
          # Still some errors left.
          for i in errs:
            Errors.display( " "*i.col, i)

        

      if Errors.count == 1:
        sys.stdout.write( '%d error detected.\n' % Errors.count )
      if Errors.count != 1:
        sys.stdout.write( '%d errors detected.\n' % Errors.count )

      if Errors.mergeErrors and Errors.count:
        sys.stdout.write( f"see {Errors.listName} for a listing showing the errors.\n")

class Parser( object ):
   _EOF = 0
   _identifier = 1
   _number = 2
   _hexnumber = 3
   _negnumber = 4
   _string = 5
   _float = 6
   _negfloat = 7
   maxT = 33

   T          = True
   x          = False
   minErrDist = 2

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

   # Struct to map ROM address ranges to symbols
   DebugInfo = {}
   AddrToSource = {}
   Tags = {}
   T_OPCODE = 0
   T_VAL = 1  

   def updateStackUse(self, maindiff, retdiff):
     self.StackUse = (self.StackUse[0] + maindiff, self.StackUse[1] + retdiff)

   def emit(self, op, otype, newop, comment=''):
      print("%5d" % self.Addr, "%6s" % op, "  ", comment)
      if op in self.Opcodes.OPCODESET:
        self.updateStackUse(*self.Opcodes.OPCODEDICT[op])
        self.ROM.append(self.Opcodes.OPCODENUM[op])
      else:
        self.ROM.append(op)

      if (op == ';') or (op == 'EXIT'):
        print("Stack delta:", self.StackUse)
        self.checkWordStacks()
        currentword = self.WordList[-1]
        self.WordStackUse[currentword] = self.StackUse

      self.AddrToSource[int(self.Addr)] = (newop, otype, self.token.pos, self.token.line, self.token.col, self.token.val, self.ROM[-1])
      self.Addr += 1

   def checkWordStacks(self):
      currentword = self.WordList[-1]
      if currentword in self.WordStackUse:
        # Check that stack use matches at all exits
        u = self.WordStackUse[currentword]
        if self.StackUse != u:
          self.SemErr( f"Stack usage must be the same at all word exits. Previous = {u}, current = {self.StackUse}." )

   def addWord(self, wordstr):
      if wordstr not in self.Words:
        self.StackUse = (0,0)
        self.Words[wordstr] = (self.WordCnt, self.Addr)
        self.WordList.append(wordstr)
        print(": %s" % wordstr)
        self.WordCnt += 1
        return wordstr
      else:
        self.SemErr(f"'{wordstr}' already defined: ")

   def addGlobal(self, gstr):
     if gstr not in self.Globals:
       self.Globals[gstr] = self.GlobalLastAddr
       print("GLOBAL: %s" % gstr)
       self.GlobalLastAddr += 4
     else:
       self.SemErr(f"'{gstr}' already defined: ")       

   def addLabel(self, label):
     labelname = self.WordList[-1] + '::' + label
     if labelname in self.Labels:
       self.SemErr("Label already defined: " + labelname)
     else:
       self.Labels[labelname] = self.Addr
       print("{%s}" % labelname)

   def addTag(self, tag):
     self.Tags[self.Addr] = tag
     print("%5d" % self.Addr, "<%s>" % tag)

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

      # Maybe it's a global
      if wordstr in self.Globals:
        val = self.Globals[wordstr]
        self.emitVal(val, comment = "// %s (%d)" % (wordstr, val))
        return

      self.SemErr(f"Didn't know what to do with: '{wordstr}'. It's not an opcode, word, known constant, or label." )  

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
       self.SemErr( "The word 'RunShot' must be defined." )
     if "Idle" not in self.Words:
       self.SemErr( "The word 'Idle' must be defined." )
     if "Halt" not in self.Words:
       self.SemErr( "The word 'Halt' must be defined." )

   def checkPathsEqual(self, p1, p2):
     if (p1[0] != p2[0]) or (p1[1] != p2[1]):
       self.SemErr( f"Both paths through a conditional should have the same effect on stack sizes, {p1} vs {p2}" )

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


   def __init__( self ):
      self.scanner     = None
      self.token       = None           # last recognized token
      self.la          = None           # lookahead token
      self.genScanner  = False
      self.tokenString = ''             # used in declarations of literal tokens
      self.noString    = '-none-'       # used in declarations of literal tokens
      self.errDist     = Parser.minErrDist

   def getParsingPos( self ):
      return self.la.line, self.la.col

   def SynErr( self, errNum ):
      if self.errDist >= Parser.minErrDist:
         Errors.SynErr( errNum )

      self.errDist = 0

   def SemErr( self, msg ):
      if self.errDist >= Parser.minErrDist:
         Errors.SemErr( msg )

      self.errDist = 0

   def Warning( self, msg ):
      if self.errDist >= Parser.minErrDist:
         Errors.Warn( msg )

      self.errDist = 0

   def Successful( self ):
      return Errors.count == 0;

   def LexString( self ):
      return self.token.val

   def LookAheadString( self ):
      return self.la.val

   def Get( self ):
      while True:
         self.token = self.la
         self.la = self.scanner.Scan( )
         if self.la.kind <= Parser.maxT:
            self.errDist += 1
            break
         
         self.la = self.token

   def Expect( self, n ):
      if self.la.kind == n:
         self.Get( )
      else:
         self.SynErr( n )

   def StartOf( self, s ):
      return self.set[s][self.la.kind]

   def ExpectWeak( self, n, follow ):
      if self.la.kind == n:
         self.Get( )
      else:
         self.SynErr( n )
         while not self.StartOf(follow):
            self.Get( )

   def WeakSeparator( self, n, syFol, repFol ):
      s = [ False for i in range( Parser.maxT+1 ) ]
      if self.la.kind == n:
         self.Get( )
         return True
      elif self.StartOf(repFol):
         return False
      else:
         for i in range( Parser.maxT ):
            s[i] = self.set[syFol][i] or self.set[repFol][i] or self.set[0][i]
         self.SynErr( n )
         while not s[self.la.kind]:
            self.Get( )
         return self.StartOf( syFol )

   def EFroth( self ):
      self.Expect(8)
      self.Expect(5)
      self.Expect(9)
      self.Expect(2)
      self.MaxVol = int(self.token.val) 
      self.Expect(9)
      self.Expect(2)
      self.MaxSec = int(self.token.val) 
      self.Expect(10)
      self.Program()
      self.checkWords() 

   def Program( self ):
      while self.la.kind == 11:
         self.Global()

      while self.la.kind == 12 or self.la.kind == 14:
         self.Word()


   def Global( self ):
      self.Expect(11)
      self.Expect(1)
      self.addGlobal(self.token.val) 

   def Word( self ):
      if self.la.kind == 12:
         while not (self.la.kind == 0 or self.la.kind == 12):
            self.SynErr(34)
            self.Get()
         self.AnnotatedWord()
      elif self.la.kind == 14:
         self.SimpleWord()
      else:
         self.SynErr(35)

   def AnnotatedWord( self ):
      self.Expect(12)
      while self.la.kind == 1:
         self.Get( )

      self.ExpectWeak(13, 1)
      while self.la.kind == 1:
         self.Get( )

      self.Expect(10)
      self.RestOfWord()

   def SimpleWord( self ):
      self.Expect(14)
      self.RestOfWord()

   def RestOfWord( self ):
      name = self.WordDef()
      while self.StartOf(2):
         self.CompoundStatement()

      self.EndOfWord()

   def WordDef( self ):
      self.Expect(1)
      name = self.addWord(self.token.val)        
      return name

   def CompoundStatement( self ):
      if self.la.kind == 15:
         self.If()
      elif self.la.kind == 18:
         self.For()
      elif self.la.kind == 20:
         self.Repeat()
      elif self.la.kind == 22:
         self.While()
      elif self.StartOf(3):
         self.Statement()
      else:
         self.SynErr(36)

   def EndOfWord( self ):
      self.emit(";", self.T_OPCODE, 1)           
      self.Expect(28)

   def If( self ):
      self.Expect(15)
      self.emitAddr(0, addfixup=True)             
      self.emitWord("BZ")                         
      stackbeforeif = self.StackUse               
      while self.StartOf(2):
         self.CompoundStatement()

      while self.la.kind == 16:
         tofix = self.Fixups.pop()                   
         self.emitAddr(0, addfixup=True)             
         self.emitWord("BRA")                        
         stackbeforeelse = self.StackUse             
         self.Get( )
         self.doFixup(tofix, self.Addr);             
         self.StackUse = stackbeforeif               
         while self.StartOf(2):
            self.CompoundStatement()

         self.checkPathsEqual(stackbeforeelse, self.StackUse) 

      self.Expect(17)
      self.doFixup(self.Fixups.pop(), self.Addr)  
      self.StackUse = stackbeforeif               

   def For( self ):
      self.Expect(18)
      self.startFor(); addr = self.Addr-1         
      while self.StartOf(2):
         self.CompoundStatement()

      self.Expect(19)
      self.endFor(addr)                           

   def Repeat( self ):
      self.Expect(20)
      while self.StartOf(2):
         self.CompoundStatement()

      self.Expect(21)

   def While( self ):
      self.Expect(22)
      while self.StartOf(2):
         self.CompoundStatement()

      self.Expect(23)

   def Statement( self ):
      if self.la.kind == 1:
         self.WordName()
      elif self.StartOf(4):
         self.Number()
      elif self.la.kind == 29:
         self.Label()
      elif self.StartOf(5):
         self.MathOp()
      elif self.la.kind == 31:
         self.Tag()
      else:
         self.SynErr(37)

   def WordName( self ):
      self.Expect(1)
      self.emitWord(self.token.val)              

   def Number( self ):
      val = self.IntOrFloat()
      self.emitVal(val, comment="// %s" % self.token.val) 

   def Label( self ):
      self.Expect(29)
      self.Expect(1)
      self.addLabel(self.token.val)              
      self.Expect(30)

   def MathOp( self ):
      if self.la.kind == 24:
         self.Get( )
      elif self.la.kind == 25:
         self.Get( )
      elif self.la.kind == 26:
         self.Get( )
      elif self.la.kind == 27:
         self.Get( )
      else:
         self.SynErr(38)
      self.emitWord(self.token.val)              

   def Tag( self ):
      self.Expect(31)
      self.Expect(1)
      self.addTag(self.token.val)                
      self.Expect(32)

   def IntOrFloat( self ):
      if self.la.kind == 2:
         self.Get( )
         val = int(self.token.val, 10)              
      elif self.la.kind == 3:
         self.Get( )
         val = int(self.token.val, 16)              
      elif self.la.kind == 6:
         self.Get( )
         val = float(self.token.val)                
      elif self.la.kind == 4:
         self.Get( )
         val = int(self.token.val, 10)              
      elif self.la.kind == 7:
         self.Get( )
         val = float(self.token.val)                
      else:
         self.SynErr(39)
      return val



   def Parse( self, scanner ):
      self.scanner = scanner
      self.la = Token( )
      self.la.val = ''
      self.Get( )
      self.EFroth()
      self.Expect(0)


   set = [
      [T,x,x,x, x,x,x,x, x,x,x,x, T,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x],
      [T,T,x,x, x,x,x,x, x,x,T,x, T,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x],
      [x,T,T,T, T,x,T,T, x,x,x,x, x,x,x,T, x,x,T,x, T,x,T,x, T,T,T,T, x,T,x,T, x,x,x],
      [x,T,T,T, T,x,T,T, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, T,T,T,T, x,T,x,T, x,x,x],
      [x,x,T,T, T,x,T,T, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x],
      [x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, x,x,x,x, T,T,T,T, x,x,x,x, x,x,x]

      ]

   errorMessages = {
      
      0 : "EOF expected",
      1 : "identifier expected",
      2 : "number expected",
      3 : "hexnumber expected",
      4 : "negnumber expected",
      5 : "string expected",
      6 : "float expected",
      7 : "negfloat expected",
      8 : "\"Program(\" expected",
      9 : "\",\" expected",
      10 : "\")\" expected",
      11 : "\"Global\" expected",
      12 : "\":(\" expected",
      13 : "\"--\" expected",
      14 : "\":\" expected",
      15 : "\"IF\" expected",
      16 : "\"ELSE\" expected",
      17 : "\"ENDIF\" expected",
      18 : "\"FOR\" expected",
      19 : "\"ENDFOR\" expected",
      20 : "\"REPEAT\" expected",
      21 : "\"ENDREPEAT\" expected",
      22 : "\"WHILE\" expected",
      23 : "\"ENDWHILE\" expected",
      24 : "\"-\" expected",
      25 : "\"+\" expected",
      26 : "\"*\" expected",
      27 : "\"/\" expected",
      28 : "\";\" expected",
      29 : "\"{\" expected",
      30 : "\"}\" expected",
      31 : "\"<\" expected",
      32 : "\">\" expected",
      33 : "??? expected",
      34 : "this symbol not expected in Word",
      35 : "invalid Word",
      36 : "invalid CompoundStatement",
      37 : "invalid Statement",
      38 : "invalid MathOp",
      39 : "invalid IntOrFloat",
      }


