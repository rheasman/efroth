
import sys

class Token( object ):
   def __init__( self ):
      self.kind   = 0     # token kind
      self.pos    = 0     # token position in the source text (starting at 0)
      self.col    = 0     # token column (starting at 0)
      self.line   = 0     # token line (starting at 1)
      self.val    = ''   # token value
      self.next   = None  # AW 2003-03-07 Tokens are kept in linked list


class Position( object ):    # position of source code stretch (e.g. semantic action, resolver expressions)
   def __init__( self, buf, beg, len, col ):
      assert isinstance( buf, Buffer )
      assert isinstance( beg, int )
      assert isinstance( len, int )
      assert isinstance( col, int )

      self.buf = buf
      self.beg = beg   # start relative to the beginning of the file
      self.len = len   # length of stretch
      self.col = col   # column number of start position

   def getSubstring( self ):
      return self.buf.readPosition( self )

class Buffer( object ):
   EOF      = '\u0100'     # 256

   def __init__( self, s ):
      self.buf    = s
      self.bufLen = len(s)
      self.pos    = 0
      self.lines  = s.splitlines( True )

   def Read( self ):
      if self.pos < self.bufLen:
         result = self.buf[self.pos]
         self.pos += 1
         return result
      else:
         return Buffer.EOF

   def ReadChars( self, numBytes=1 ):
      result = self.buf[ self.pos : self.pos + numBytes ]
      self.pos += numBytes
      return result

   def Peek( self ):
      if self.pos < self.bufLen:
         return self.buf[self.pos]
      else:
         return Scanner.buffer.EOF

   def getString( self, beg, end ):
      s = ''
      oldPos = self.getPos( )
      self.setPos( beg )
      while beg < end:
         s += self.Read( )
         beg += 1
      self.setPos( oldPos )
      return s

   def getPos( self ):
      return self.pos

   def setPos( self, value ):
      if value < 0:
         self.pos = 0
      elif value >= self.bufLen:
         self.pos = self.bufLen
      else:
         self.pos = value

   def readPosition( self, pos ):
      assert isinstance( pos, Position )
      self.setPos( pos.beg )
      return self.ReadChars( pos.len )

   def __iter__( self ):
      return iter(self.lines)

class Scanner(object):
   EOL     = '\n'
   eofSym  = 0

   charSetSize = 256
   maxT = 36
   noSym = 36
   start = [
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  1,  6,  0,  0,  0,  1,  4,  0, 18, 25, 24, 17, 32,  1, 26,
    14, 13, 13, 13, 13, 13, 13, 13, 13, 13, 34, 27, 30,  0, 31,  0,
     1,  1,  1, 35, 37,  1,  1,  1,  1,  1,  1, 36,  1,  1,  1,  1,
    33,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  0,  1,  0,  1,
     0,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
     1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1, 28,  0, 29,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
     -1]


   def __init__( self, s ):
      self.buffer = Buffer( str(s) ) # the buffer instance

      self.ch        = '\0'       # current input character
      self.pos       = -1          # column number of current character
      self.line      = 1           # line number of current character
      self.lineStart = 0           # start position of current line
      self.oldEols   = 0           # EOLs that appeared in a comment;
      self.NextCh( )
      self.ignore    = set( )      # set of characters to be ignored by the scanner
      self.ignore.add( ord(' ') )  # blanks are always white space
      self.ignore.add(9) 
      self.ignore.add(10) 
      self.ignore.add(11) 
      self.ignore.add(12) 

      # fill token list
      self.tokens = Token( )       # the complete input token stream
      node   = self.tokens

      node.next = self.NextToken( )
      node = node.next
      while node.kind != Scanner.eofSym:
         node.next = self.NextToken( )
         node = node.next

      node.next = node
      node.val  = 'EOF'
      self.t  = self.tokens     # current token
      self.pt = self.tokens     # current peek token

   def NextCh( self ):
      if self.oldEols > 0:
         self.ch = Scanner.EOL
         self.oldEols -= 1
      else:
         self.ch = self.buffer.Read( )
         self.pos += 1
         # replace isolated '\r' by '\n' in order to make
         # eol handling uniform across Windows, Unix and Mac
         if (self.ch == '\r') and (self.buffer.Peek() != '\n'):
            self.ch = Scanner.EOL
         if self.ch == Scanner.EOL:
            self.line += 1
            self.lineStart = self.pos + 1
      



   def Comment0( self ):
      level = 1
      line0 = self.line
      lineStart0 = self.lineStart
      self.NextCh()
      if self.ch == '*':
         self.NextCh()
         while True:
            if self.ch == '*':
               self.NextCh()
               if self.ch == '/':
                  level -= 1
                  if level == 0:
                     self.oldEols = self.line - line0
                     self.NextCh()
                     return True
                  self.NextCh()
            elif self.ch == Buffer.EOF:
               return False
            else:
               self.NextCh()
      else:
         if self.ch == Scanner.EOL:
            self.line -= 1
            self.lineStart = lineStart0
         self.pos = self.pos - 2
         self.buffer.setPos(self.pos+1)
         self.NextCh()
      return False

   def Comment1( self ):
      level = 1
      line0 = self.line
      lineStart0 = self.lineStart
      self.NextCh()
      if self.ch == '/':
         self.NextCh()
         while True:
            if ord(self.ch) == 10:
               level -= 1
               if level == 0:
                  self.oldEols = self.line - line0
                  self.NextCh()
                  return True
               self.NextCh()
            elif self.ch == Buffer.EOF:
               return False
            else:
               self.NextCh()
      else:
         if self.ch == Scanner.EOL:
            self.line -= 1
            self.lineStart = lineStart0
         self.pos = self.pos - 2
         self.buffer.setPos(self.pos+1)
         self.NextCh()
      return False


   def CheckLiteral( self ):
      lit = self.t.val
      if lit == "Global":
         self.t.kind = 11
      elif lit == "IF":
         self.t.kind = 15
      elif lit == "ELSE":
         self.t.kind = 16
      elif lit == "ENDIF":
         self.t.kind = 17
      elif lit == "FOR":
         self.t.kind = 18
      elif lit == "ENDFOR":
         self.t.kind = 19
      elif lit == "REPEAT":
         self.t.kind = 20
      elif lit == "ENDREPEAT":
         self.t.kind = 21
      elif lit == "WHILE":
         self.t.kind = 22
      elif lit == "ENDWHILE":
         self.t.kind = 23


   def NextToken( self ):
      while ord(self.ch) in self.ignore:
         self.NextCh( )
      if (self.ch == '/' and self.Comment0() or self.ch == '/' and self.Comment1()):
         return self.NextToken()

      self.t = Token( )
      self.t.pos = self.pos
      self.t.col = self.pos - self.lineStart + 1
      self.t.line = self.line
      if ord(self.ch) < len(self.start):
         state = self.start[ord(self.ch)]
      else:
         state = 0
      buf = u''
      buf += str(self.ch)
      self.NextCh()

      done = False
      while not done:
         if state == -1:
            self.t.kind = Scanner.eofSym     # NextCh already done
            done = True
         elif state == 0:
            self.t.kind = Scanner.noSym      # NextCh already done
            done = True
         elif state == 1:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 2:
            if (self.ch >= '0' and self.ch <= '9'
                 or self.ch >= 'A' and self.ch <= 'F'):
               buf += str(self.ch)
               self.NextCh()
               state = 3
            else:
               self.t.kind = Scanner.noSym
               done = True
         elif state == 3:
            if (self.ch >= '0' and self.ch <= '9'
                 or self.ch >= 'A' and self.ch <= 'F'):
               buf += str(self.ch)
               self.NextCh()
               state = 3
            else:
               self.t.kind = 3
               done = True
         elif state == 4:
            if (ord(self.ch) <= 9
                 or ord(self.ch) >= 11 and self.ch <= '&'
                 or self.ch >= '(' and ord(self.ch) <= 255 or ord(self.ch) > 256):
               buf += str(self.ch)
               self.NextCh()
               state = 5
            else:
               self.t.kind = Scanner.noSym
               done = True
         elif state == 5:
            if (ord(self.ch) <= 9
                 or ord(self.ch) >= 11 and self.ch <= '&'
                 or self.ch >= '(' and ord(self.ch) <= 255 or ord(self.ch) > 256):
               buf += str(self.ch)
               self.NextCh()
               state = 5
            elif ord(self.ch) == 39:
               buf += str(self.ch)
               self.NextCh()
               state = 8
            else:
               self.t.kind = Scanner.noSym
               done = True
         elif state == 6:
            if (ord(self.ch) <= 9
                 or ord(self.ch) >= 11 and self.ch <= '!'
                 or self.ch >= '#' and ord(self.ch) <= 255 or ord(self.ch) > 256):
               buf += str(self.ch)
               self.NextCh()
               state = 7
            else:
               self.t.kind = Scanner.noSym
               done = True
         elif state == 7:
            if (ord(self.ch) <= 9
                 or ord(self.ch) >= 11 and self.ch <= '!'
                 or self.ch >= '#' and ord(self.ch) <= 255 or ord(self.ch) > 256):
               buf += str(self.ch)
               self.NextCh()
               state = 7
            elif self.ch == '"':
               buf += str(self.ch)
               self.NextCh()
               state = 8
            else:
               self.t.kind = Scanner.noSym
               done = True
         elif state == 8:
            self.t.kind = 5
            done = True
         elif state == 9:
            if (self.ch >= '0' and self.ch <= '9'):
               buf += str(self.ch)
               self.NextCh()
               state = 10
            else:
               self.t.kind = Scanner.noSym
               done = True
         elif state == 10:
            if (self.ch >= '0' and self.ch <= '9'):
               buf += str(self.ch)
               self.NextCh()
               state = 10
            else:
               self.t.kind = 6
               done = True
         elif state == 11:
            if (self.ch >= '0' and self.ch <= '9'):
               buf += str(self.ch)
               self.NextCh()
               state = 12
            else:
               self.t.kind = Scanner.noSym
               done = True
         elif state == 12:
            if (self.ch >= '0' and self.ch <= '9'):
               buf += str(self.ch)
               self.NextCh()
               state = 12
            else:
               self.t.kind = 7
               done = True
         elif state == 13:
            if (self.ch >= '0' and self.ch <= '9'):
               buf += str(self.ch)
               self.NextCh()
               state = 13
            elif self.ch == '.':
               buf += str(self.ch)
               self.NextCh()
               state = 9
            else:
               self.t.kind = 2
               done = True
         elif state == 14:
            if (self.ch >= '0' and self.ch <= '9'):
               buf += str(self.ch)
               self.NextCh()
               state = 13
            elif self.ch == 'x':
               buf += str(self.ch)
               self.NextCh()
               state = 2
            elif self.ch == '.':
               buf += str(self.ch)
               self.NextCh()
               state = 9
            else:
               self.t.kind = 2
               done = True
         elif state == 15:
            if (self.ch >= '0' and self.ch <= '9'):
               buf += str(self.ch)
               self.NextCh()
               state = 15
            elif self.ch == '.':
               buf += str(self.ch)
               self.NextCh()
               state = 11
            else:
               self.t.kind = 4
               done = True
         elif state == 16:
            self.t.kind = 8
            done = True
         elif state == 17:
            self.t.kind = 9
            done = True
         elif state == 18:
            self.t.kind = 10
            done = True
         elif state == 19:
            self.t.kind = 12
            done = True
         elif state == 20:
            self.t.kind = 13
            done = True
         elif state == 21:
            self.t.kind = 24
            done = True
         elif state == 22:
            self.t.kind = 25
            done = True
         elif state == 23:
            self.t.kind = 26
            done = True
         elif state == 24:
            self.t.kind = 28
            done = True
         elif state == 25:
            self.t.kind = 29
            done = True
         elif state == 26:
            self.t.kind = 30
            done = True
         elif state == 27:
            self.t.kind = 31
            done = True
         elif state == 28:
            self.t.kind = 32
            done = True
         elif state == 29:
            self.t.kind = 33
            done = True
         elif state == 30:
            self.t.kind = 34
            done = True
         elif state == 31:
            self.t.kind = 35
            done = True
         elif state == 32:
            if (self.ch >= '0' and self.ch <= '9'):
               buf += str(self.ch)
               self.NextCh()
               state = 15
            elif self.ch == '-':
               buf += str(self.ch)
               self.NextCh()
               state = 20
            else:
               self.t.kind = 27
               done = True
         elif state == 33:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'q'
                 or self.ch >= 's' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'r':
               buf += str(self.ch)
               self.NextCh()
               state = 38
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 34:
            if self.ch == '(':
               buf += str(self.ch)
               self.NextCh()
               state = 19
            else:
               self.t.kind = 14
               done = True
         elif state == 35:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'N'
                 or self.ch >= 'P' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'O':
               buf += str(self.ch)
               self.NextCh()
               state = 39
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 36:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'D'
                 or self.ch >= 'F' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'E':
               buf += str(self.ch)
               self.NextCh()
               state = 40
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 37:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'H'
                 or self.ch >= 'J' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'I':
               buf += str(self.ch)
               self.NextCh()
               state = 41
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 38:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'n'
                 or self.ch >= 'p' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'o':
               buf += str(self.ch)
               self.NextCh()
               state = 42
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 39:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'O'
                 or self.ch >= 'Q' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'P':
               buf += str(self.ch)
               self.NextCh()
               state = 43
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 40:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'D'
                 or self.ch >= 'F' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'E':
               buf += str(self.ch)
               self.NextCh()
               state = 44
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 41:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'R'
                 or self.ch >= 'T' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'S':
               buf += str(self.ch)
               self.NextCh()
               state = 45
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 42:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'f'
                 or self.ch >= 'h' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'g':
               buf += str(self.ch)
               self.NextCh()
               state = 46
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 43:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'X'
                 or self.ch >= 'Z' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'Y':
               buf += str(self.ch)
               self.NextCh()
               state = 47
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 44:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'O'
                 or self.ch >= 'Q' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'P':
               buf += str(self.ch)
               self.NextCh()
               state = 48
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 45:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'B'
                 or self.ch >= 'D' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'C':
               buf += str(self.ch)
               self.NextCh()
               state = 49
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 46:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'q'
                 or self.ch >= 's' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'r':
               buf += str(self.ch)
               self.NextCh()
               state = 50
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 47:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == '(':
               buf += str(self.ch)
               self.NextCh()
               state = 21
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 48:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == '(':
               buf += str(self.ch)
               self.NextCh()
               state = 22
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 49:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch == '@'
                 or self.ch >= 'B' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'A':
               buf += str(self.ch)
               self.NextCh()
               state = 51
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 50:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'b' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'a':
               buf += str(self.ch)
               self.NextCh()
               state = 52
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 51:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'Q'
                 or self.ch >= 'S' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'R':
               buf += str(self.ch)
               self.NextCh()
               state = 53
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 52:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'l'
                 or self.ch >= 'n' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'm':
               buf += str(self.ch)
               self.NextCh()
               state = 54
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 53:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= 'C'
                 or self.ch >= 'E' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == 'D':
               buf += str(self.ch)
               self.NextCh()
               state = 55
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 54:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == '(':
               buf += str(self.ch)
               self.NextCh()
               state = 16
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t
         elif state == 55:
            if (self.ch == '!'
                 or self.ch == '&'
                 or self.ch == '.'
                 or self.ch >= '0' and self.ch <= '9'
                 or self.ch >= '@' and self.ch <= '['
                 or self.ch == ']'
                 or self.ch == '_'
                 or self.ch >= 'a' and self.ch <= 'z'):
               buf += str(self.ch)
               self.NextCh()
               state = 1
            elif self.ch == '(':
               buf += str(self.ch)
               self.NextCh()
               state = 23
            else:
               self.t.kind = 1
               self.t.val = buf
               self.CheckLiteral()
               return self.t

      self.t.val = buf
      return self.t

   def Scan( self ):
      self.t = self.t.next
      self.pt = self.t.next
      return self.t

   def Peek( self ):
      self.pt = self.pt.next
      while self.pt.kind > self.maxT:
         self.pt = self.pt.next

      return self.pt

   def ResetPeek( self ):
      self.pt = self.t

