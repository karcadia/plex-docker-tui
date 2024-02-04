from os import getenv

APP_NAME                 = 'Docker TUI'
DOCKER_COMPOSE           = True
DOCKER_COMPOSE_PATH      = '/mnt/dump/docker'
PLEX_SERVER_HOST         = 'http://localhost:32400'
PLEX_API                 = PLEX_SERVER_HOST + '/status/sessions'
PLEX_TOKEN               = getenv('plex_token')
MAX_RIGHT_BAR_LENGTH     = 60
IMAGE_PULL_STACK         = 'docker-compose pull 2>&1'
UPDATE_AND_RESTART_STACK = 'docker-compose down 2>&1 && docker-compose pull 2>&1 && docker-compose up -d 2>&1 && docker image prune -f'
UPDATE_AND_STOP_STACK    = 'docker-compose down 2>&1 && docker-compose pull 2>&1'
UPDATE_OS_STACK          = 'sudo apt update 2>&1 && sudo apt upgrade -y 2>&1'
FS_COMMAND               = 'df -hl -x tmpfs'
LV_COMMAND               = 'sudo lvs -o lv_name,vg_name,attr,lvsize'
VG_COMMAND               = 'sudo vgs'
PV_COMMAND               = 'sudo pvs'
