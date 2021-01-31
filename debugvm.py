#!/usr/bin/python3
from dearpygui.core import *
from dearpygui.simple import *

import json, sys
from collections import OrderedDict
from vm import CPU
FontSize = 5
Windows = {}

VMCPU = CPU()
PREFS_FILE_NAME = 'prefs.debugvm.json'
UI_FILE_NAME = 'ui.debugvm.json'

def charW(x):
  return int(round(FontSize*x*0.49))

def charH(x):
  return int(round(FontSize*x*1.2))

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
          configure_item(name, **win)
          #set_window_pos(name, win['x_pos'], win['y_pos'])
          #set_item_width(name, win['width'])
          #set_item_height(name, win['height'])
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

def cb_step(sender, data):  
  VMCPU.step()
  update_cpu_views()


def add_controls():
  if does_item_exist("Controls"):
    delete_item("Controls")

  with window("Controls", autosize=True, x_pos=0, y_pos=0):
    with group("Buttons1", horizontal=True):
      add_button("STEP", callback=cb_step)
      add_button("OVER")
      add_button("INTO")

    with group("Buttons2", horizontal=True):
      add_button("SHOT")
      add_button("IDLE")
      add_button("HALT")

    with group("Buttons3", horizontal=True):
      add_button("RUN")

def add_editor():
  if does_item_exist("Source"):
    del Windows["Source"]
    delete_item("Source")

  Windows["Source"] = Editor("froths/Flat9.eforth")

def cb_add_controls(sender, data):
  add_controls()

def cb_add_editor(sender, data):
  add_editor()

def cb_nop(sender, data):
  pass

class Editor:
  def __init__(self, filename):
    f = open(filename, "r")
    self.TextLines = f.readlines()
    f.close()
    self.addLines()

  def addLines(self):
    longestline = max(len(x.rstrip()) for x in self.TextLines)
    with window("Program", width=charW(longestline+5), height=charH(len(self.TextLines))):
      with tab_bar("ProgramTab"):
        with tab("Source"):
          for i, line in enumerate(self.TextLines):
            with group(f"SourceLNG{i}", horizontal=True):
              add_text(f"SourceLN{i}", default_value= "%5d" % i)
              add_text(f"SourceL{i}", default_value=line)
        with tab("Opcodes"):
          add_text("Test")


class StackDisplay:
  def __init__(self, name, stack):
    self.Stack = stack
    self.Name = name
    self.createDisplay()

  def getStackVal(self, pos):
    if len(self.Stack) > pos:
      return self.Stack.read(pos)
    else:
      return 0.0

  def updateDisplay(self):
    if self.Stack.Changed:
      for i in range(64):
        set_value(f"{self.Name}val_{i}", "%08f" % self.getStackVal(i))

  def createDisplay(self):
    with window(self.Name, autosize=True):
      with child(f"{self.Name}child", autosize_x=True, height=charH(16), border=False):
        for i in range(64):
          with group(f"{self.Name}group_{i}", horizontal=True):
            add_text(f"{self.Name}pos_{i}", default_value="%02d" % i)
            add_text(f"{self.Name}val_{i}", default_value="%8f" % self.getStackVal(i))

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

  def createDisplay(self):
    with window(self.Name, autosize=True):
      with child(f"{self.Name}child", width=charW(10), height=charH(3)):
        with group(f"{self.Name}group", horizontal=True):
          add_text(f"{self.Name}PC", default_value="PC: %05d" % self.CPU.PC)

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

RenderCount = 0
def cb_render(sender, data):
  global RenderCount
  RenderCount += 1
  if RenderCount == 1:
    fix_window_positions()

def cb_close(sender, data):
  set_mouse_release_callback(None)
  set_render_callback(None)

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

      #with menu("Display"):
      #  add_menu_item("Set display size prefs", callback=callback_size_prefs)

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


  add_controls()
  add_editor()
  add_stack(VMCPU.CallStack, "CallStack")
  add_stack(VMCPU.Stack, "Stack")
  add_cpu_info(VMCPU, "CPUInfo")

  VMCPU.loadRaw('Flat9.bin')
  update_cpu_views()


  set_main_window_title("Dalgano Debugger")
  set_item_color("Main Window", mvGuiCol_WindowBg, [128, 128, 128, 0])
  set_style_global_alpha(1.0)

  set_mouse_release_callback(cb_mouse_release)
  set_render_callback(cb_render)
  restore_ui()
  start_dearpygui(primary_window="Main Window")


if __name__ == '__main__':
  main()