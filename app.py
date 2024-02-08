# Imports
from os import chdir
from sys import stdout
from time import sleep
from subprocess import run, Popen, PIPE
from xml.etree import ElementTree
# end stdlib
from requests import get, ConnectionError
from psutil import cpu_count, cpu_times_percent, virtual_memory, net_io_counters
from textual import on
from textual.app import App
from textual.widgets import Button, Header, Footer, DataTable, Log, Static, Label
from docker import from_env

# Load config
from config import *

# Init
docker = from_env()

# Global Functions
def docker_ps():
  container_list = []
  header_tuple = ('Name', 'Id', 'Image', 'Created', 'Status', 'Since')
  container_list.append(header_tuple)
  containers = docker.containers.list()
  for con in containers:
    con_created = con.attrs['Created'].split('.')[0]
    con_started = con.attrs['State']['StartedAt'].split('.')[0]
    if len(con.image.attrs['RepoTags']) > 0:
      con_image = con.image.attrs['RepoTags'][0]
    else:
      con_image = con.image.attrs['RepoTags']
    con_tuple = (con.name, con.short_id, con_image, con_created, con.status, con_started)
    container_list.append(con_tuple)
  return container_list

def refresh_plex(transcode_toggle):
  report = ''
  headers = {'X-Plex-Token': PLEX_TOKEN}
  try:
    plex_sessions_xml = get(PLEX_API, headers=headers)
  except ConnectionError:
    return 'Unable to connect to Plex API.'
  xml_tree = ElementTree.fromstring(plex_sessions_xml.text)
  streams = []
  for stream in xml_tree:
    stream_item = {}
    stream_item['type'] = stream.attrib['type']
    stream_item['title'] = stream.attrib['title']
    if 'parentTitle' in stream.attrib.keys():
      if stream_item['type'] == 'episode':
        stream_item['season'] = stream.attrib['parentTitle']
      elif stream_item['type'] == 'track':
        stream_item['album'] = stream.attrib['parentTitle']
    if 'grandparentTitle' in stream.attrib.keys():
      if stream_item['type'] == 'episode':
        stream_item['tv_show'] = stream.attrib['grandparentTitle']
      elif stream_item['type'] == 'track':
        stream_item['artist'] = stream.attrib['grandparentTitle']
      else:
        stream_item['grandparent'] = stream.attrib['grandparentTitle']
    for child in stream:
      if child.tag == 'User' and 'title' in child.attrib.keys():
        stream_item['user'] = child.attrib['title']
      if child.tag == 'Session' and 'location' in child.attrib.keys():
        stream_item['location'] = child.attrib['location']
      if child.tag == 'Session' and 'bandwidth' in child.attrib.keys():
        stream_item['bandwidth'] = child.attrib['bandwidth']
      if child.tag == 'Player' and 'state' in child.attrib.keys():
        stream_item['state'] = child.attrib['state']
      if child.tag == 'Player' and 'remotePublicAddress' in child.attrib.keys():
        stream_item['ip'] = child.attrib['remotePublicAddress']
      if child.tag == 'Player' and 'device' in child.attrib.keys():
        stream_item['device'] = child.attrib['device']
      if child.tag == 'Player' and 'platform' in child.attrib.keys():
        stream_item['platform'] = child.attrib['platform']
      if child.tag == 'Player' and 'platformVersion' in child.attrib.keys():
        stream_item['platform_version'] = child.attrib['platformVersion']
      if child.tag == 'Player' and 'product' in child.attrib.keys():
        stream_item['product'] = child.attrib['product']
      if child.tag == 'Player' and 'title' in child.attrib.keys():
        stream_item['machine'] = child.attrib['title']
      if child.tag == 'Director' and 'tag' in child.attrib.keys():
        stream_item['director'] = child.attrib['tag']
      if transcode_toggle:
        if child.tag == 'TranscodeSession' and 'progress' in child.attrib.keys():
          stream_item['transcode_progress'] = float(child.attrib['progress']) // 1
        if child.tag == 'TranscodeSession' and 'complete' in child.attrib.keys():
          stream_item['transcode_complete'] = child.attrib['complete']
        if child.tag == 'TranscodeSession' and 'throttled' in child.attrib.keys():
          stream_item['transcode_throttled'] = child.attrib['throttled']
        if child.tag == 'TranscodeSession' and 'videoDecision' in child.attrib.keys():
          stream_item['transcode_video'] = child.attrib['videoDecision']
        if child.tag == 'TranscodeSession' and 'audioDecision' in child.attrib.keys():
          stream_item['transcode_audio'] = child.attrib['audioDecision']
        if child.tag == 'TranscodeSession' and 'subtitleDecision' in child.attrib.keys():
          stream_item['transcode_subtitle'] = child.attrib['subtitleDecision']
    streams.append(stream_item)

  shrunk_report = ''
  for stream in streams:
    shrunk_report += shrink_dict(stream)
    shrunk_report += '-\n'
  report += shrunk_report

  return report

def shrink_dict(in_dict):
  if type(in_dict) is not dict:
    return 'Error: Can only shrink dicts.'
  current_length = 0
  line = ''
  shrunk_report = ''
  for key in in_dict.keys():
    value = in_dict[key]
    line += f'{key}: {value} '
    current_length = len(line)
    if current_length > MAX_RIGHT_BAR_LENGTH:
      line += '\n'
      shrunk_report += line
      line = ''
      current_length = 0
  if line:
    shrunk_report += line + '\n'
  return shrunk_report

def convert_bytes(in_bytes):
  if type(in_bytes) is not int:
    return 'Error: Can only convert integers.'

  if in_bytes > 1000000000000:
    out = str(in_bytes // 1000000000000) + 'T'
  elif in_bytes > 1000000000:
    out = str(in_bytes // 1000000000) + 'G'
  elif in_bytes > 1000000:
    out = str(in_bytes // 1000000) + 'M'
  elif in_bytes >= 1000:
    out = str(in_bytes // 1000) + 'K'
  elif in_bytes < 1000:
    out = str(in_bytes) + 'B'

  return out

# Classes
class MenuApp(App):
  # Class Vars
  BINDINGS = [("a", "all_toggles", "All Toggles"),
              ("c", "cpu_toggle", "CPU Toggle"),
              ("d", "toggle_dark", "Dark Mode Toggle"),
              ("e", "edit_docker", "Edit docker-compose file"),
              ("f", "fs_toggle", "Filesystem Toggle"),
              ("l", "lv_toggle", "LV Toggle"),
              ("m", "memory_toggle", "Memory Toggle"),
              ("n", "network_toggle", "Network Toggle"),
              ("p", "pv_toggle", "PV Toggle"),
              ("t", "transcode_toggle", "Transcode Toggle"),
              ("q", "quit", "Quit"),
              ("v", "vg_toggle", "VG Toggle"),
              ("x", "plex_toggle", "Plex Toggle")]
  CSS_PATH = "grid.tcss"

  # Place our components on the grid and activate each one.
  def compose(self):
    yield Button('Pull\nContainer\nImages', id='pull_images')
    yield DataTable(id='dt1')
    yield Label('Loading...', id='stats')
    yield Button('Update\nand Stop\nContainers', id='update_and_stop')
    yield Button('Update/Patch\nOS', id='update_os')
    yield Log(id='log1')
    yield Button('Update and\nRestart\nContainers', id='update_and_restart')
    yield Header()
    yield Footer()

  # Once the app inits (one-time).
  def on_mount(self):
    self.title = APP_NAME
    self.refresh_stats()
    self.refresh_container_table()
    self.set_interval(5, self.refresh_container_table)
    self.set_interval(2, self.refresh_stats_launcher)
    self.start_watching_logs()

  async def refresh_stats_launcher(self):
    self.run_worker(self.refresh_stats(), exclusive=True, thread=True)

  async def start_watching_logs(self):
    self.run_worker(self.watch_smartmontools(), exclusive=True, thread=True)

  async def watch_smartmontools(self):
    log = self.query_one('#log1')
    self.sub_title = 'SmartMonTools Job Running'
    bash_command_stack = 'sudo journalctl -u smartmontools 2>&1'
    process = Popen(bash_command_stack, shell=True, stderr=PIPE, stdout=PIPE)
    for line in process.stdout:
      log.write(line.decode())

  # Refresh the stats and update the module.
  async def refresh_stats(self):
    # Connect to our stats log so we can update it.
    stats = self.query_one('#stats')

    # Build the report.
    report = ''
    # Storage
    if self.fs_toggle:
      report += '---\n'
      df = run(FS_COMMAND, shell=True, capture_output=True)
      stdout = df.stdout.decode()
      report += stdout
    if self.vg_toggle:
      report += '---\n'
      vgs = run(VG_COMMAND, shell=True, capture_output=True)
      stdout = vgs.stdout.decode()
      if stdout:
        report += stdout
    if self.pv_toggle:
      report += '---\n'
      pvs = run(PV_COMMAND, shell=True, capture_output=True)
      stdout = pvs.stdout.decode()
      if stdout:
        report += stdout
    if self.lv_toggle:
      report += '---\n'
      lvs = run(LV_COMMAND, shell=True, capture_output=True)
      stdout = lvs.stdout.decode()
      if stdout:
        report += stdout
    # CPU
    if self.cpu_toggle:
      report += '---\n'
      report += 'CPU\n'
      cpu_usage = cpu_times_percent()._asdict()
      cpu_usage['count'] = cpu_count()
      report += shrink_dict(cpu_usage)
    # Memory
    if self.memory_toggle:
      report += '---\n'
      report += 'Memory\n'
      memory_usage = virtual_memory()._asdict()
      for key in memory_usage.keys():
        if type(memory_usage[key]) is int:
          memory_usage[key] = convert_bytes(memory_usage[key])
      report += shrink_dict(memory_usage)
    # Network
    if self.network_toggle:
      report += '---\n'
      report += 'Network\n'
      first_network_usage = net_io_counters()._asdict()
      sleep(1)
      second_network_usage = net_io_counters()._asdict()
      diff_sent_bytes = second_network_usage['bytes_sent'] - first_network_usage['bytes_sent']
      diff_recv_bytes = second_network_usage['bytes_recv'] - first_network_usage['bytes_recv']
      diff_sent = convert_bytes(diff_sent_bytes)
      diff_recv = convert_bytes(diff_recv_bytes)
      second_network_usage['send_rate'] = diff_sent + '/s'
      second_network_usage['recv_rate'] = diff_recv + '/s'
      for key in second_network_usage.keys():
        if key[0:3] != 'err' and key[0:4] != 'drop' and type(second_network_usage[key]) is int:
          second_network_usage[key] = convert_bytes(second_network_usage[key])
      report += shrink_dict(second_network_usage)
    # Plex
    if self.plex_toggle:
      report += '---\n' + 'Plex\n'
      if PLEX_TOKEN:
        report += refresh_plex(self.transcode_toggle)
      else:
        report += 'Valid environment variable plex_token required.'

    # Update our stats log with our report content.
    stats.update(report)

  # Our custom class function to refresh the container data table.
  def refresh_container_table(self):
    table = self.query_one(DataTable)
    ROWS = docker_ps()
    table.clear(columns=True)
    table.add_columns(*ROWS[0])
    table.add_rows(ROWS[1:])

  # Once the app inits (one-time).
  def on_ready(self):
    log = self.query_one('#log1')
    log.write(f'Welcome to {APP_NAME}.\n')
    self.vg_toggle        = True
    self.pv_toggle        = True
    self.lv_toggle        = True
    self.cpu_toggle       = True
    self.memory_toggle    = True
    self.fs_toggle        = True
    self.network_toggle   = True
    self.plex_toggle      = True
    self.transcode_toggle = True
    self.all_toggles      = True

  # Launch the update_and_restart function when the button is pressed.
  @on(Button.Pressed, "#update_and_restart")
  def update_and_restart_launcher(self):
    log = self.query_one('#log1')
    log.write_line('Starting Docker Update and Restart...\n\r')
    self.run_worker(self.update_and_restart(), exclusive=True, thread=True)

  async def update_and_restart(self):
    self.sub_title = 'Job Running'
    log = self.query_one('#log1')
    chdir(DOCKER_COMPOSE_PATH)
    bash_command_stack = UPDATE_AND_RESTART_STACK
    process = Popen(bash_command_stack, shell=True, stderr=PIPE, stdout=PIPE)
    for line in process.stdout:
      log.write(line.decode())
    self.refresh_container_table()
    self.sub_title = 'Job Complete'
    log.write('Done.\n')

  # Launch the update_and_stop function when the button is pressed.
  @on(Button.Pressed, "#update_and_stop")
  def update_and_stop_launcher(self):
    log = self.query_one('#log1')
    log.write('Starting Docker Update and Stop...\n\r')
    self.run_worker(self.update_and_stop(), exclusive=True, thread=True)

  async def update_and_stop(self):
    self.sub_title = 'Job Running'
    log = self.query_one('#log1')
    chdir(DOCKER_COMPOSE_PATH)
    bash_command_stack = UPDATE_AND_STOP_STACK
    process = Popen(bash_command_stack, shell=True, stderr=PIPE, stdout=PIPE)
    for line in process.stdout:
      log.write(line.decode())
    self.refresh_container_table()
    self.sub_title = 'Job Complete'
    log.write('Done.\n')
 
  # Launch the update_os function when the button is pressed.
  @on(Button.Pressed, "#update_os")
  def update_os_launcher(self):
    log = self.query_one('#log1')
    log.write('Starting OS Update...\n')
    self.run_worker(self.update_os(), exclusive=True, thread=True)

  async def update_os(self):
    self.sub_title = 'Job Running'
    log = self.query_one('#log1')
    bash_command_stack = UPDATE_OS_STACK
    process = Popen(bash_command_stack, shell=True, stderr=PIPE, stdout=PIPE)
    for line in process.stdout:
      log.write(line.decode())
    self.sub_title = 'Job Complete'
    log.write('Done.\n')
    
  @on(Button.Pressed, "#pull_images")
  def pull_images_launcher(self):
    log = self.query_one('#log1')
    log.write('Starting Docker Compose Pull...\n')
    self.run_worker(self.pull_images(), exclusive=True, thread=True)

  async def pull_images(self):
    self.sub_title = 'Job Running'
    log = self.query_one('#log1')
    chdir(DOCKER_COMPOSE_PATH)
    bash_command_stack = IMAGE_PULL_STACK
    process = Popen(bash_command_stack, shell=True, stderr=PIPE, stdout=PIPE)
    for line in process.stdout:
      log.write(line.decode())
    self.sub_title = 'Job Complete'
    log.write('Done.\n')

  def action_toggle_dark(self):
    self.dark = not self.dark

  def action_edit_docker(self):
    chdir(DOCKER_COMPOSE_PATH)
    run('vi docker-compose.yml', shell=True)

  def action_vg_toggle(self):
    self.vg_toggle = not self.vg_toggle

  def action_pv_toggle(self):
    self.pv_toggle = not self.pv_toggle

  def action_lv_toggle(self):
    self.lv_toggle = not self.lv_toggle

  def action_cpu_toggle(self):
    self.cpu_toggle = not self.cpu_toggle

  def action_memory_toggle(self):
    self.memory_toggle = not self.memory_toggle

  def action_fs_toggle(self):
    self.fs_toggle = not self.fs_toggle

  def action_network_toggle(self):
    self.network_toggle = not self.network_toggle

  def action_plex_toggle(self):
    self.plex_toggle = not self.plex_toggle

  def action_transcode_toggle(self):
    self.transcode_toggle = not self.transcode_toggle

  def action_all_toggles(self):
    self.all_toggles    = not self.all_toggles
    self.vg_toggle      = self.all_toggles
    self.pv_toggle      = self.all_toggles
    self.lv_toggle      = self.all_toggles
    self.cpu_toggle     = self.all_toggles
    self.memory_toggle  = self.all_toggles
    self.fs_toggle      = self.all_toggles
    self.network_toggle = self.all_toggles
    self.plex_toggle    = self.all_toggles

  def action_quit(self):
    exit(0)

# Main
if __name__ == '__main__':
  app = MenuApp()
  app.run()
