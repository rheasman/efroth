#!/usr/bin/python3
from dearpygui.core import *
from dearpygui.simple import *

from disasm import DebugDis
import json, sys, random
from collections import OrderedDict
from vm import *
import systemtime

FontSize = 5
Windows = {}
CharW = 1
CharH = 1

SYSTIME = systemtime.SystemTime()
VMCPU = CPU(SYSTIME)
PREFS_FILE_NAME = 'prefs.debugvm.json'
UI_FILE_NAME = 'ui.debugvm.json'

def charW(x):
  return int(round(x*CharW))

def charH(x):
  return int(round(x*CharH))

def add_default_prefs():
  add_value("Display DPI", 160.0)
  add_value("Font height (mm)", 4.0)

def set_from_prefs_dict(prefs):
  print("Loading prefs from prefs.json: ")
  for i in prefs:
    set_value(i, prefs[i])
    print("  %s: %s" % (i, prefs[i]))

def save_prefs():
  prefs = OrderedDict()
  dpi = get_value("Display DPI")
  height = get_value("Font height (mm)")

  prefs["Display DPI"] = dpi
  prefs["Font height (mm)"] = height
  with open(PREFS_FILE_NAME, 'w') as outfile:
    json.dump(prefs, outfile, indent=2)
    outfile.close()

def load_prefs():
  try:
    with open(PREFS_FILE_NAME, 'r') as infile:
      prefs = json.load(infile)
      set_from_prefs_dict(prefs)
  except FileNotFoundError:
    # No prefs file, so save defaults to create new prefs file
    save_prefs()

def save_ui():
  wlist = get_windows()
  wlist.remove('filedialog')
  vp = {"ViewportSize" : get_main_window_size()}
  config = [vp]
  for win in wlist:
    config.append(get_item_configuration(win))

  with open(UI_FILE_NAME, 'w') as outfile:
    json.dump(config, outfile, indent=2)


def cb_save_ui(sender, data):
  save_ui()


def delkeys(dict, keys):
  for key in keys:
    try:
        del dict[key]
    except KeyError:
      pass

def restore_ui():
  try:
    with open(UI_FILE_NAME, 'r') as infile:
      config = json.load(infile)
      viewportinfo, config = config[0], config[1:]
      set_main_window_size(viewportinfo['ViewportSize'][0], viewportinfo['ViewportSize'][1])
      for win in config:
        name = win['name']
        if does_item_exist(name):
          #print(f"Config for {name} : {win}\n")
          delkeys(win, ["source", "tip", "enabled", "menubar"])
          iconfig = {}
          for i in ("x_pos", "y_pos", "width", "height", "enabled", "show"):
            if i in win:
              iconfig[i] = win[i]
          
          #print(win)
          configure_item(name, **iconfig)
  except FileNotFoundError:
    pass

def cb_restore_ui(sender, data):
  restore_ui()

def log_callback(sender, data):
  log_debug(f"{sender} ran a callback its value is {get_value(sender)}")

def setupFonts():
  dpi = get_value("Display DPI")
  height = get_value("Font height (mm)")
  # Use Mononoki font, 0.25 inches high
  global FontSize
  FontSize = int(round(height/25.4*dpi))

  add_additional_font("fonts/mononoki-Regular.ttf", FontSize)
  #add_additional_font("fonts/FiraCode-Regular.otf", FontSize)
  #add_additional_font("fonts/Inconsolata.otf", FontSize)
  #add_additional_font("fonts/ProggyClean.ttf", FontSize)
  #add_additional_font("fonts/TerminusTTF-4.46.0.ttf", FontSize)

def cb_set_display_DPI(sender, data):
  print(sender, data)
  setupFonts()

def cb_set_font_height(sender, data):
  print(sender, data)
  setupFonts()

def callback_size_prefs(sender, data):
  with window("Display Preferences", autosize=True):  
    add_drag_float("Display DPI", callback=cb_set_display_DPI,
      default_value=160,
      min_value=10,
      max_value=300,
      clamped=True,
      )
    add_drag_float("Font height (mm)", callback=cb_set_font_height,
      default_value=4.0,
      min_value=1.0,
      max_value=20.0,
      clamped=True
      )

def callback_load_exe(sender, data):
  print(sender, data)

def update_cpu_views():
  if "CallStack" in Windows:
    Windows["CallStack"].updateDisplay()
  if "Stack" in Windows:
    Windows["Stack"].updateDisplay()
  if "CPUInfo" in Windows:
    Windows["CPUInfo"].updateDisplay()

  if "Program" in Windows:
    Windows["Program"].updateDisplay()

def cb_run(sender, data):
  if "Program" not in Windows:
    return

  try:
    VMCPU.step(ignorebp=VMCPU.PC)
    update_cpu_views()
    while True:
      VMCPU.step()
      if random.random() < 0.01: # Don't update UI every step... can be slow
        update_cpu_views()
  except VMCPUStopped:
    update_cpu_views()
  except VMCPUBreakpoint:
    update_cpu_views()

def cb_step(sender, data):  
  if "Program" not in Windows:
    return
  
  try:
    VMCPU.step(ignorebp=VMCPU.PC)
    update_cpu_views()
  except VMCPUStopped:
    update_cpu_views()
  except VMCPUBreakpoint:
    update_cpu_views()

def cb_out(sender, data):  
  if "Program" not in Windows:
    return
  
  try:
    while VMCPU.getCurrentOpcodeName()!= ";":
      VMCPU.step(ignorebp=VMCPU.PC)
      update_cpu_views()
    VMCPU.step(ignorebp=VMCPU.PC)
    update_cpu_views()      
  except VMCPUStopped:
    update_cpu_views()
  except VMCPUBreakpoint:
    update_cpu_views()

def cb_lstep(sender, data):  
  # Step opcode execution until associated source line changes
  if "Program" not in Windows:
    return

  try:
    editor = Windows["Program"]

    currentpc = VMCPU.PC
    currentline = editor.D.getSourceLineForAddr(VMCPU.PC)
    line = currentline
    while (line == currentline):
      VMCPU.step(ignorebp=currentpc)
      update_cpu_views()
      line = editor.D.getSourceLineForAddr(VMCPU.PC)

  except VMCPUStopped:
    update_cpu_views()
  except VMCPUBreakpoint:
    update_cpu_views()

# def step_opcode():
#   addr = VMCPU.PC
#   nextaddr = VMCPU.nextOpcodeAddr(addr)
#   while VMCPU.PC != nextaddr:
#     VMCPU.step()

def cb_nextl(sender, data):
  # Step opcode execution until source line increments, ignoring subroutines
  if "Program" not in Windows:
    return

  try:
    editor = Windows["Program"]

    currentop = VMCPU.getOpcodeName(VMCPU.ROM[VMCPU.PC])
    if currentop == ';':
      cb_step(sender, data)
      return

    # TODO: FOR is going to create some interesting corner cases. Will deal with it later.

    currentpc = VMCPU.PC
    currentline = editor.D.getSourceLineForAddr(VMCPU.PC)
    line = currentline
    nextlineaddr = editor.D.getAddrForSourceLine(currentline+1)
    while line == currentline:
      while VMCPU.PC != nextlineaddr:
        VMCPU.step(ignorebp=currentpc)
        if random.random() < 0.05:
          update_cpu_views()    # Update UI 5% of the time
      update_cpu_views()

      line = editor.D.getSourceLineForAddr(VMCPU.PC)    

  except VMCPUStopped:
    update_cpu_views()
  except VMCPUBreakpoint:
    update_cpu_views()

def cb_over(sender, data):
  # Step opcode execution until source line changes, without viewing subroutines
  if "Program" not in Windows:
    return

  try:
    editor = Windows["Program"]

    currentop = VMCPU.getOpcodeName(VMCPU.ROM[VMCPU.PC])
    if currentop == ';':
      cb_step(sender, data)
      return

    currentpc = VMCPU.PC
    currentline = editor.D.getSourceLineForAddr(VMCPU.PC)
    line = currentline
    
    while line == currentline:
      if VMCPU.isCurrentOpCall():
        # It's a call to a subroutine. Run until we get out.
        nextlineaddr = editor.D.getAddrForSourceLine(line+1)
        while VMCPU.PC != nextlineaddr:
          VMCPU.step(ignorebp=currentpc)
      else:
        # Not a call. Just execute an opcode
        VMCPU.step(ignorebp=currentpc)

      update_cpu_views()
      line = editor.D.getSourceLineForAddr(VMCPU.PC)    

  except VMCPUStopped:
    update_cpu_views()
  except VMCPUBreakpoint:
    update_cpu_views()

def cb_shot(sender, data):
  SYSTIME.reset()
  VMCPU.reset()
  VMCPU.moveToWord("RunShot")
  update_cpu_views()

def cb_idle(sender, data):
  VMCPU.reset()
  VMCPU.moveToWord("Idle")
  update_cpu_views()

def cb_halt(sender, data):
  VMCPU.reset()
  VMCPU.moveToWord("Halt")
  update_cpu_views()

def add_controls():
  if does_item_exist("Controls"):
    delete_item("Controls")

  with window("Controls", autosize=True, x_pos=0, y_pos=0):
    with group("Buttons1", horizontal=True):
      w = charW(6)
      add_button("STEP",  width=w, callback=cb_step,  tip="Run one instruction")
      add_button("STEPL", width=w, callback=cb_lstep, tip="Run one source line of code")
      add_button("NEXTL", width=w, callback=cb_nextl, tip="Run until next source line of code")

    with group("Buttons2", horizontal=True):
      add_button("OVER", width=w, callback=cb_over, tip="Run one line of code, don't show subroutines")
      add_button("OUT",  width=w, callback=cb_out,  tip="Run until ';' is executed")
      add_button("RUN",  width=w, callback=cb_run,  tip="Run until completion, or a breakpoint")

    with group("Buttons3", horizontal=True):
      add_button("SHOT", width=w, callback=cb_shot,   tip="Move to 'RunShot'")
      add_button("IDLE", width=w, callback=cb_idle,   tip="Move to 'Idle'")
      add_button("HALT", width=w, callback=cb_halt,   tip="Move to 'Halt'")


  for item in get_item_children("Controls"):
    set_item_style_var(item, mvGuiStyleVar_FrameRounding, [charH(1)*0.3])
    set_item_style_var(item, mvGuiStyleVar_FramePadding, [charW(1)*0.3, 1])

def add_editor():
  if does_item_exist("Program"):
    del Windows["Program"]
    delete_item("Program")

  Windows["Program"] = Editor("froths/Flat9.debug")

def cb_add_controls(sender, data):
  add_controls()

def cb_add_editor(sender, data):
  add_editor()

def cb_nop(sender, data):
  pass

def hsv_to_rgb(h: float, s: float, v: float, a:float) -> (float, float, float, float):
    if s == 0.0: return (v, v, v, 255*a)
    i = int(h*6.) 
    f = (h*6.)-i; p,q,t = v*(1.-s), v*(1.-s*f), v*(1.-s*(1.-f)); i%=6
    if i == 0: return (255*v, 255*t, 255*p, 255*a)
    if i == 1: return (255*q, 255*v, 255*p, 255*a)
    if i == 2: return (255*p, 255*v, 255*t, 255*a)
    if i == 3: return (255*p, 255*q, 255*v, 255*a)
    if i == 4: return (255*t, 255*p, 255*v, 255*a)
    if i == 5: return (255*v, 255*p, 255*q, 255*a)


class Editor:
  def __init__(self, filename):
    self.D = DebugDis(filename)
    self.TextLines = self.D.SourceLines
    self.addLines()
    self.Selected = None

  def selectMemAddr(self, addr):
    """
    Highlight the line of code associated with the CPU program counter
    """
    oldaddr = self.Selected
    if oldaddr != None:
      sl = self.D.getSourceLineForAddr(oldaddr)
      item = f"SourceL{sl}"
      #for item in get_item_children(f"SourceG{sl}"):
      set_item_color(item, mvGuiCol_Button, [0,0,0,0])

    self.Selected = addr

    if self.Selected != None:
      sl = self.D.getSourceLineForAddr(addr)
      #for item in get_item_children(f"SourceG{sl}"):
      item = f"SourceL{sl}"
      set_item_color(item, mvGuiCol_Button, hsv_to_rgb(4/7.0, 0.8, 0.8, 1.0))

      #set_item_color(f"SourceLNG{sl}", mvGuiCol_Text, [155,0,75,175])
      #configure_item(f"SourceL{sl}", enabled=True)


      #print(get_item_configuration(f"SourceL{sl}"))

  def updateDisplay(self):
    self.selectMemAddr(VMCPU.PC)

  def cb_addr_click(self, sender, data):
    #print(sender, data)
    VMCPU.toggleBP(data)
    item = f"SourceLN{self.D.getSourceLineForAddr(data)}"
    i = 4
    hovercol = hsv_to_rgb(i/7.0, 0.7, 0.7, 0.3)
    if VMCPU.isBP(data):
      set_item_color(item, mvGuiCol_Button, hsv_to_rgb(i/7.0, 0.8, 0.8, 1.0))
      set_item_color(item, mvGuiCol_ButtonHovered, hsv_to_rgb(i/7.0, 0.8, 0.8, 1.0))
      configure_item(item, tip="Breakpoint at Addr %d" % data)
    else:
      set_item_color(item, mvGuiCol_Button, [0,0,0,0])
      set_item_color(item, mvGuiCol_ButtonHovered, hovercol)
      configure_item(item, tip="")


  def addLine(self, name, count, field1, field2, padto, cb, cb_data):
    field2 = field2 + (' '*(padto-len(field2))) + ' '
    with group(f"{name}G{count}", horizontal=True):
      add_button(f"{name}LN{count}", label = field1, callback=cb, callback_data=cb_data)
      if field2 == '':
        add_button(f"{name}L{count}",  label = ' ')
      else:
        add_button(f"{name}L{count}",  label = field2)

    i = 4
    hovercol = hsv_to_rgb(i/7.0, 0.7, 0.7, 0.3)
    for item in get_item_children(f"{name}G{count}"):
      set_item_color(item, mvGuiCol_Button, [0,0,0,0])
      set_item_color(item, mvGuiCol_ButtonHovered, hovercol)
      set_item_color(item, mvGuiCol_ButtonActive, hsv_to_rgb(i/7.0, 0.8, 0.8, 1.0))
      set_item_style_var(item, mvGuiStyleVar_FrameRounding, [2])
      set_item_style_var(item, mvGuiStyleVar_FramePadding, [1, 1])

  def addLines(self):
    longestline = max(len(x.rstrip()) for x in self.TextLines)
    with window("Program", x_pos=400, y_pos=200, width=charW(longestline+12), height=charH(40), no_scrollbar=True):
      with tab_bar("ProgramTab"):
        with tab("Source"):
          with child("SourceChild", autosize_x=True, autosize_y=True):
            for i, line in enumerate(self.TextLines, start=1):
              addr = self.D.getAddrForSourceLine(i)
              self.addLine("Source", i, "%5d" % i, line, longestline, self.cb_addr_click, addr)
    
        with tab("Opcodes"):
          memdump = self.D.dumpOpcodes()
          for i, op in enumerate(memdump):
            addr = op[0]
            with group(f"opcodesLG{addr}", horizontal=True):
              add_text(f"opcodeAddr{addr}", default_value= "%5d" % op[0])
              add_text(f"opcodeBytes{addr}", default_value= " ".join([ "%02X" % x for x in op[1]]))
              if op[2]:
                add_text(f"opcodeval{i}", default_value= ("%d" % op[2]))
                add_text(f"opcodesym{i}", default_value='('+op[3]+')')
              else:
                add_text(f"opcodesym{i}", default_value=op[3])




class StackDisplay:
  def __init__(self, name, stack):
    self.Stack = stack
    self.Name = name
    self.createDisplay()

  def getStackVal(self, pos):
    if len(self.Stack) > pos:
      return self.Stack.read(pos)
    else:
      return None

  def updateDisplay(self):
    if self.Stack.Changed:
      for i in range(64):
        sv = self.getStackVal(i)
        if sv != None:
          #print(get_item_configuration(f"{self.Name}val_{i}"))
          configure_item(f"{self.Name}val_{i}", label=("%12.6f" % self.getStackVal(i).float))
          set_value(f"{self.Name}sym_{i}", self.getStackVal(i).symbol)
          configure_item(f"{self.Name}sym_{i}", tip=self.getStackVal(i).symbol)
        else:
          configure_item(f"{self.Name}val_{i}", label="------------")
          set_value(f"{self.Name}sym_{i}", '')
          configure_item(f"{self.Name}sym_{i}", tip='')

  def createDisplay(self):
    with window(self.Name, autosize=True):
      with child(f"{self.Name}child", width=charW(40), height=charH(16), border=False):
        for i in range(64):
          with group(f"{self.Name}group_{i}", horizontal=True):
            add_text(f"{self.Name}pos_{i}", default_value="%02d" % i)
            sv = self.getStackVal(i)
            if sv != None:
              with tree_node(f"{self.Name}val_{i}", label="%12.6f" % self.getStackVal(i).float, default_open=True):
                add_text(f"{self.Name}sym_{i}", default_value=self.getStackVal(i).symbol)
            else:
              with tree_node(f"{self.Name}val_{i}", label="------------", default_open=True):
                add_text(f"{self.Name}sym_{i}", default_value='')

def add_stack(stack, name):
  if does_item_exist(name):
    del Windows[name]
    delete_item(name)

  Windows[name] = StackDisplay(name, stack)

class CPUInfo:
  def __init__(self, cpu, name):
    self.Name = name
    self.CPU = cpu
    self.createDisplay()

  def updateDisplay(self):
    set_value(f"{self.Name}PC", "PC: %05d" % self.CPU.PC)
    set_value(f"{self.Name}Cycles", "Cycles: %06d" % self.CPU.Cycles)

  def createDisplay(self):
    with window(self.Name, autosize=True):
      with child(f"{self.Name}child", width=charW(16), height=charH(3)):
        with group(f"{self.Name}group"):
          add_text(f"{self.Name}PC", default_value="PC: %05d" % self.CPU.PC)
          add_text(f"{self.Name}Cycles", default_value="Cycles: %06d" % self.CPU.Cycles)

def add_cpu_info(cpu, name):
  if does_item_exist(name):
    del Windows[name]
    delete_item(name)

  Windows[name] = CPUInfo(cpu, name)




def fix_window_positions():
  wp = get_style_frame_padding()
  mbw, mbh = [int(x) for x in get_item_rect_size("MenuBar")]
  windows = get_windows()
  windows = [x for x in windows if x != "Main Window"]
  for i in windows:
    x, y = [int(x) for x in get_window_pos(i)]

    fix = False
    if x < 0:
      x = 0
      fix = True

    if y < mbh:
      y = mbh+int(wp[1])
      fix = True
    
    if fix:
      set_window_pos(i, x, y)

def cb_mouse_release(sender, data):
  fix_window_positions()

def cb_close(sender, data):
  set_mouse_release_callback(None)
  set_render_callback(None)

def add_de1graph():
  with window("Graphs"):
    add_plot("DE1", x_axis_name="Time/[s]", y_axis_name="Pressure",
      yaxis2=True,
      yaxis3=True

      )

def setup_UI(sender, data):
  global CharW
  global CharH

  x, y = get_item_rect_size("CharRuler")
  print(x,y)
  CharW = float(x/100)
  CharH = float(y/10)

  print(f"Character width  is: {CharW}")
  print(f"Character height is: {CharH}")
  delete_item("CharRuler")

  add_controls()
  add_editor()
  add_stack(VMCPU.CallStack, "CallStack")
  add_stack(VMCPU.Stack, "Stack")
  add_cpu_info(VMCPU, "CPUInfo")

  VMCPU.loadDebug('froths/Flat9.debug')
  update_cpu_views()


  set_main_window_title("Dalgona Debugger")
  set_item_color("Main Window", mvGuiCol_WindowBg, [128, 128, 128, 0])
  set_style_global_alpha(1.0)

  set_mouse_release_callback(cb_mouse_release)
  restore_ui()
  fix_window_positions()

def main():
  add_default_prefs()
  load_prefs()


  set_theme("Dark")
  setupFonts()
  #enable_docking(dock_space=True, shift_only=False)
  #set_style_window_rounding(charH(0.25))
  #set_style_frame_rounding(charH(0.25))

  with window("Main Window", label="Espresso Forth Debugger", width=160, height=120, on_close=cb_close):
    with menu_bar("MenuBar"):
      with menu("File"):
        add_menu_item("Load Exe", callback=callback_load_exe)

      with menu("Windows"):
        add_menu_item("Save Layout", label="Save Layout", callback=cb_save_ui)
        add_menu_item("Restore Layout", label="Restore Layout", callback=cb_restore_ui)
        add_menu_item("ControlsMI", label="Controls", callback=cb_add_controls)
        add_menu_item("EditorMI", label="Editor", callback=cb_add_editor)

      with menu("Extras"):
        add_menu_item("Show Logger", callback=show_logger)
        add_menu_item("Show About", callback=show_about)
        add_menu_item("Show Metrics", callback=show_metrics)
        add_menu_item("Show Documentation", callback=show_documentation)
        add_menu_item("Show Debug", callback=show_debug)
        add_menu_item("Show Style Editor", callback=show_style_editor)

    add_text("CharRuler", default_value = ("\n".join(['H'*100]*10))) #, color=[0,0,0,0])

  add_de1graph()

  set_start_callback(setup_UI)

  try:
    with open(UI_FILE_NAME, 'r') as infile:
      config = json.load(infile)
      viewportinfo, config = config[0], config[1:]
      set_main_window_size(viewportinfo['ViewportSize'][0], viewportinfo['ViewportSize'][1])
  except FileNotFoundError:
    pass

  start_dearpygui(primary_window="Main Window")


if __name__ == '__main__':
  main()