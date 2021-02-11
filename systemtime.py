#!/usr/bin/env python3
#!/usr/bin/python3

class SystemTime:
  """
  System time, measured in 6000ths of a second.
  """
  def __init__(self):
    self.reset()

  def reset(self):
    self.Ticks = 0

  def getTicksPerSecond(self):
    return 6000

  def waitTilNextACZero(self):
    togo = self.Ticks % 50
    if togo == 0:
      # Already on an AC Zero Cross
      return

    togo = 50 - togo # Calculate ticks to go
    self.Ticks += togo

  def addTicks(self, ticks):
    self.Ticks += ticks

  def getTicks(self):
    return self.Ticks

  def getS(self):
    return self.Ticks/6000.0

  def addMS(self, ms):
    self.addTicks(int(round(ms*6)))

  def addS(self, s):
    self.addTicks(int(round(s/6000.0)))