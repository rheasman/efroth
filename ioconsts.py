import collections
class IOConsts:
  IODICT = collections.OrderedDict([
    ("IO_Pressure"         , "RWT"),  # R = Readable. W = Writeable. T = Can read back
    ("IO_Flow"             , "RWT"),
    ("IO_ShowerTemp"       , "RWT"),
    ("IO_GroupMetalTemp"   , "RWT"),
    ("IO_GroupInletTemp"   , "RWT"),
    ("IO_Vol"              , "R"),
    ("IO_NumSeconds"       , "R"),
    ("IO_ReportedState"    , "W")
  ])

  IOCONSTVAL = {}
  IOCONSTNAME = {}
  for v, k in enumerate(IODICT):
    IOCONSTVAL[k] = v
    IOCONSTNAME[v] = k

  # 0 : Pressure (IO_Pressure)
  # 1 : Shower head temperature
  # 2 : Group head temperature
  # 3 : Group inlet temperature
  # 4 : Estimated flow
  # 5 : Estimated volume since start of shot
  # 6 : Number of seconds since start of shot
  # 7 : Number of seconds since start of frame
  # 8 : Reported State. Use this to report where you are. See REPORTEDSTATES



  REPORTEDSTATES = [
    "Ready"             # 0 Ready
    "NotReady",         # 1 Tells the app that some kind of waiting is going on
    "PreInfuse",        # 2 Espresso only. Hot Water and Steam will skip this state.
    "Pour",             # 3 Not used in Steam
    "Flush"             # 4 Espresso only, atm
  ]

  VALIDESPRESSOSTATES = [0,1,2,3,4]

if __name__ == '__main__':
  I = IOConsts()
  print(I.IOCONSTNAME)
  print(I.IOCONSTVAL)