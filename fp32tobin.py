#!/usr/bin/python3
from math import *
from struct import *

def fracToInt(frac):
  #print(frac)
  res = 0
  bits = 0
  bita = []
  while (frac > 0.0) and (bits < 23):
    frac *= 2
    if frac >= 1.0:
      bit = 1
      frac -= 1.0
    else:
      bit = 0
    res = (res << 1) | bit
    bita.append(bit)
    bits += 1
    #print(bits, frac)

  # if (bits == 24):
  #   bits = 23
  #   if res & 1:
  #     # Round up LSB
  #     res = (res >> 1) | 1
  #   else:
  #     res = res >> 1

  print("         "+format(res, "023b"), bits)
  return res << (23-bits)

def floatAsBits(f):
  sign_bit = (f < 0.0)
  f = abs(f)

  scaledf = f
  exp = 0
  while (exp > -126) and (scaledf <= (1.0/(1<<23))):
    scaledf *= 2
    exp -= 1

  # 1 0111 1111 00000000000000000000000
  #exp = int(math.log(f)/math.log(2))
  print("Exp:",exp)
  #print(scaledf)
  intbits = int(scaledf)
  fbits = fracToInt(scaledf % 1)

  if (exp <= -126):
    # Subnormal number
    exp = 0
    return (sign_bit << 31) | (exp << 23) | ( fbits & 0x7FFFFF )    
  
  if intbits == 0:
    # May need to shift fractional part left
    while fbits < (1 << 23): 
      exp -= 1
      fbits = fbits << 1

  bits = (intbits << 23) | fbits
  if intbits >= 2:
    while intbits >= 2:
      exp += 1
      intbits = intbits >> 1
      bits = bits >> 1

  print("Exp2:", exp)
  exp += 127
  if (exp < 0):
    exp = 0

  return (sign_bit << 31) | (exp << 23) | ( bits & 0x7FFFFF )

def bstr(x):
  return format(x, "032b")

def test(name, bitpattern, floatval):
  bp0 = pack(">f", floatval)
  bp  = unpack(">I", bp0)[0]
  str0 = bstr(bp)

  print("%s:" % name)
  str1 = bstr(bitpattern)
  str2 = bstr(floatAsBits(floatval))

  if str1 != str2:
    print("****************************** Didn't match: ")

  print("  Packed:", str0)
  print("  Target:", str1)
  print("  Result:", str2)
  print()

if __name__ == "__main__": 
  test("Pi", 0x40490fdb, 3.14159274101257324)

  test("math.Pi", 0x40490fdb, pi)

  test("-2", 0xc0000000, -2)

  test("2", 0x40000000, 2)

  test("Smallest positive subnormal", 0x00000001, pow(2, -149))

  test("Smallest normal number", 0x00800000, pow(2, -126))

  test("Smallest normal number*2", 0x01000000, pow(2, -125))

  test("92.5", 0x42b90000, 92.5)

