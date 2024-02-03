# Imports
from os import chdir, listdir, getenv
from sys import stdout
from subprocess import run, Popen, PIPE
from xml.etree import ElementTree
# end stdlib
from requests import get
from psutil import cpu_count, cpu_times_percent, virtual_memory, net_io_counters
from textual import on
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Button, Header, Footer, DataTable, Log, Static, Label
from docker import from_env

# Vars
APP_NAME             = 'Docker TUI'
DOCKER_COMPOSE       = True
DOCKER_COMPOSE_PATH  = '/mnt/dump/docker'
PLEX_SERVER_HOST     = 'http://localhost:32400'
PLEX_API             = PLEX_SERVER_HOST + '/status/sessions'
PLEX_TOKEN           = None
PLEX_TOKEN           = getenv('plex_token')
MAX_RIGHT_BAR_LENGTH = 80

# Init
docker = from_env()

# Global Functions
def docker_ps():
  container_list = []
  header_tuple = ('Name', 'Id', 'Image', 'Created', 'Status', 'Since')
  container_list.append(header_tuple)
  containers = docker.containers.list()
  for con in containers:
    con_tuple = (con.name, con.short_id, con.image.attrs['RepoTags'][0], con.attrs['Created'].split('.')[0], con.status, con.attrs['State']['StartedAt'].split('.')[0])
    container_list.append(con_tuple)
  return container_list

def refresh_plex():
  report = ''
  report += '---\n'
  report += 'Plex\n'
  headers = {'X-Plex-Token': PLEX_TOKEN}
  plex_sessions_xml = get(PLEX_API, headers=headers)
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
      if child.tag == 'Director' and 'tag' in child.attrib.keys():
        stream_item['director'] = child.attrib['tag']
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
    if current_length < MAX_RIGHT_BAR_LENGTH:
      line += f'{key}: {value} '
      current_length += len(line)
    else:
      shrunk_report += line + '\n'
      line = f'{key}: {value} '
      current_length = len(line)
  return shrunk_report

# Classes
class MenuApp(App):
  # Class Vars
  BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
              ("e", "edit_docker", "Edit docker-compose file"),
              ("q", "quit", "Quit")]
  CSS_PATH = "grid.tcss"

  # Place our components on the grid and activate each one.
  def compose(self):
    yield Button('Pull Container Images', id='pull_images')
    yield DataTable(id='dt1')
    yield Log('Storage Statistics Loading...', id='stats')
    yield Button('Update and Stop Containers', id='update_and_stop')
    yield Button('Update (Patch) OS', id='update_os')
    yield Log(id='log1')
    yield Button('Update and Restart Containers', id='update_and_restart')
    yield Header()
    yield Footer()

  # Once the app inits (one-time).
  def on_mount(self):
    self.title = APP_NAME
    self.refresh_container_table()
    self.refresh_stats()
    self.set_interval(5, self.refresh_container_table)
    self.set_interval(2, self.refresh_stats)

  # Refresh the stats and update the module.
  def refresh_stats(self):
    # Connect to our stats log so we can update it.
    stats = self.query_one('#stats')
    stats.clear()

    # Get a set (forced-unique list) of disks.
    disks = set()
    for file in listdir('/dev'):
      if file[0:2] == 'sd':
        disks.add(file[0:3])

    # Convert the set to a list and sort.
    sorted_disks = list(disks)
    sorted_disks.sort()

    # Build the report.
    report = ''
    # Storage
    report += '---\n'
    df = run('df -hl -x tmpfs', shell=True, capture_output=True)
    stdout = df.stdout.decode()
    report += stdout
    report += '---\n'
    vgs = run('sudo vgs', shell=True, capture_output=True)
    stdout = vgs.stdout.decode()
    if stdout:
      report += stdout
      report += '---\n'
    pvs = run('sudo pvs', shell=True, capture_output=True)
    stdout = pvs.stdout.decode()
    if stdout:
      report += stdout
      report += '---\n'
#    Output needs cleaned, kinda stuck, dont care that much.
#    lvs = run('sudo lvs', shell=True, capture_output=True)
#    stdout = lvs.stdout.decode()
#    if stdout:
#      report += stdout
#      report += '---\n'
    # CPU
    report += 'CPU\n'
    cpu_usage = cpu_times_percent()._asdict()
    cpu_usage['count'] = cpu_count()
    report += shrink_dict(cpu_usage)
    report += '---\n'
    # Memory
    report += 'Memory\n'
    memory_usage = virtual_memory()._asdict()
    report += shrink_dict(memory_usage)
    report += '---\n'
    # Network
    report += 'Network\n'
    network_usage = net_io_counters()._asdict()
    report += shrink_dict(network_usage)
    # Plex
    if PLEX_TOKEN:
      report += refresh_plex()

    # Update our stats log with our report content.
    stats.write(report)

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
    bash_command_stack = 'docker-compose down 2>&1 && docker-compose pull 2>&1 && docker-compose up -d 2>&1 && docker image prune -f'
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
    bash_command_stack = 'docker-compose down 2>&1 && docker-compose pull 2>&1'
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
    bash_command_stack = 'sudo apt update 2>&1 && sudo apt upgrade -y 2>&1'
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
    bash_command_stack = 'docker-compose pull 2>&1'
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

  def action_quit(self):
    exit(0)

# Main
if __name__ == '__main__':
  app = MenuApp()
  app.run()
