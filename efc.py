#!/usr/bin/python3
from Scanner import *
from Parser import *
import sys, os

def main(filetoparse):
  filebase = filetoparse.rsplit(".", 1)[0]
  dirName, fileName = os.path.split(filetoparse)

  f = open(filetoparse, "r")
  s = f.read()
  f.close()

  scanner = Scanner(s)
  parser = Parser()
  
  Errors.Init(fileName, dirName, True, parser.getParsingPos, parser.errorMessages)

  parser.Parse( scanner )
  Errors.Summarize( scanner.buffer )

  if (Errors.count == 0):
    # Dump result
    parser.writeResults(filetoparse, filebase)
  else:
    sys.exit(1)

if __name__ == '__main__':
  main(sys.argv[1])