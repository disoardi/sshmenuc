import argparse
import json
import os
import re

import readchar
import sys
import time

from subprocess import call, Popen, PIPE
from clint import resources
from clint.textui import puts, colored

targets = []
config_name = ''

# Time to sleep between transitions
TRANSITION_DELAY_TIME = 0.5

NUMBER_ENTRY_EXPIRE_TIME = 0.75


def main():
    global config_name
    global targets

    # Check arguments
    parser = argparse.ArgumentParser(prog='sshmenu',
                                     description='A convenient tool for bookmarking '
                                                 'hosts and connecting to them via ssh.')
    parser.add_argument('-c', '--configname', default='config', help='Specify an alternate configuration name.')
    args = parser.parse_args()

    # Get config name
    config_name = '{configname}.json'.format(configname=args.configname)

    # First parameter is 'company' name, hence duplicate arguments
    resources.init('sshmenu', 'sshmenu')

    # For the first run, create an example config
    if resources.user.read(config_name) is None:
        example_config = {
            'targets': [
                {
                    'host': 'user@example-machine.local',
                    'friendly': 'This is an example target',
                    'options': []
                },
                {
                    'command': 'mosh',
                    'host': 'user@example-machine.local',
                    'friendly': 'This is an example target using mosh',
                    'options': []
                }
            ]
        }
        resources.user.write(config_name, json.dumps(example_config, indent=4))
        # update_target()

    #    display_menu_tg()
    #    targets = json.loads(resources.user.read(config_name))
    #    config = targets['targets']

    #    display_menu(config)

    update_targets()
    display_menu(targets)


def update_targets():
    global targets, config_name

    config = json.loads(resources.user.read(config_name))
    if 'targets' in config:
        targets = config['targets']


def get_terminal_height():
    # Return height of terminal as int
    tput = Popen(['tput', 'lines'], stdout=PIPE)
    height, stderr = tput.communicate()

    return int(height)

def display_help():
    # Clear screen and show the help text
    call(['clear'])
    puts(colored.cyan('Available commands (press any key to exit)'))

    puts(' enter       - Connect to your selection')
    puts(' crtl+c | q  - Quit sshmenu')
    puts(' k (up)      - Move your selection up')
    puts(' j (down)    - Move your selection down')
    puts(' h           - Show help menu')
    puts(' c           - Create new connection')
    puts(' d           - Delete connection')
    puts(' e           - Edit connection')
    puts(' + (plus)    - Move connection up')
    puts(' - (minus)   - Move connection down')

    # Hang until we get a keypress
    readchar.readkey()

def display_menu(targets):
    global config_name
    # Save current cursor position so we can overwrite on list updates
    call(['tput',  'sc'])

    # Keep track of currently selected target
    selected_target = 0

    # Support input of long numbers
    number_buffer = []

    # Store time of last number that was entered
    time_last_digit_pressed = round(time.time())

    # Get initial terminal height
    terminal_height = get_terminal_height()

    # Set initial visible target range.
    # Subtract 2 because one line is used by the instructions,
    # and one line is always empty at the bottom.
    visible_target_range = range(terminal_height - 2)

    number_last = round(time.time())

    while True:
        # Return to the saved cursor position
        call(['tput', 'clear', 'rc'])

        # We need at least one target for our UI to make sense
        num_targets = len(targets)
        if num_targets <= 0:
            puts(colored.red('Whoops, you don\'t have any connections defined in your config!'))
            puts('')
            puts('Press "c" to create a new connection')
        else:
            puts(colored.cyan('Select a target (press "h" for help)'))

            # Determine the longest host
            longest_host = -1
            longest_line = -1
            longest_user = 5
            longest_note = 5

            for index, target in enumerate(targets):

                # Host to connect
                if 'host' in target:
                    length = len(list(target['host']))
                    # Check host length
                    if length > longest_host:
                        longest_host = length

                if 'options' in target:
                    length_opt = len(re.sub('(-l)', 'User: ', re.sub('(\[|]|\')', ' ', str(target['options'])).split(',')[0]))
                    # Check host length
                    if length_opt > longest_user:
                        longest_user = length_opt
                else:
                    length = len(list(target.keys())[0])
                    # Check host length
                    if length > longest_host:
                        longest_host = length

                if longest_note > longest_user:
                    longest_user = longest_note
                else:
                    longest_note = longest_user

            if 'host' in target:
                # Header
                puts(colored.yellow("+--------+-" + "-" * longest_host + "-+-" + "-" * longest_user + "-+"))
                puts(colored.yellow('| ' + "ID    " + ' | ' + u'Host'.ljust(longest_host) + ' | ' + u'User'.ljust(longest_user) + ' |'))
                puts(colored.yellow("+--------+-" + "-" * longest_host + "-+-" + "-" * longest_user + "-+"))
            else:
                # Header
                puts(colored.yellow("+--------+-" + "-" * longest_host + "-+-" + "-" * longest_note + "-+"))
                puts(colored.yellow('| ' + "ID    " + ' | ' + u'Group'.ljust(longest_host) + ' | ' + u'Note'.ljust(longest_note) + ' |'))
                puts(colored.yellow("+--------+-" + "-" * longest_host + "-+-" + "-" * longest_note + "-+"))

            for index, target in enumerate(targets):

                # Host to connect
                if 'host' in target:
                    if 'options' in target:
                        user = re.sub('(-l)', 'User: ', re.sub('(\[|]|\')', '', str(target['options'])).split(',')[0])

                    else:
                        user = ''
                    if index == selected_target:
                        puts(colored.yellow('|') + colored.green('-> ') + colored.green('%2d ' % index) + colored.yellow('  | ') + colored.green(target['host'].ljust(longest_host)) + colored.yellow(' |') + colored.green(user.ljust(longest_user)) + colored.yellow('  |'))
                    else:
                        puts(colored.yellow('|   ') + '%2d ' % index + colored.yellow('  | ') + target['host'].ljust(longest_host) + colored.yellow(' |') + user.ljust(longest_user) + colored.yellow('  |'))

                # Group of hosts
                else:

                    if index == selected_target:
                        if list(target.keys())[0] == 'note':
                            puts(colored.yellow('|') + colored.green('-> ') + colored.green('%2d ' % index) + colored.yellow('  | ') + colored.green(list(target.keys())[0].ljust(longest_host)) + colored.yellow(' |') + target['note'].ljust(longest_note) + colored.yellow('  |'))
                        else:
                            puts(colored.yellow('|') + colored.green('-> ') + colored.green('%2d ' % index) + colored.yellow('  | ') + colored.green(list(target.keys())[0].ljust(longest_host)) + colored.yellow(' |') + ''.ljust(longest_note) + colored.yellow('  |'))
                    else:
                        puts(colored.yellow('|   ') + '%2d ' % index + colored.yellow('  | ') + list(target.keys())[0].ljust(longest_host) + colored.yellow(' |') + ''.ljust(longest_note) + colored.yellow('  |'))
            if 'host' in target:
                if 'options' in target:
                    puts(colored.yellow("+--------+-" + "-" * longest_host + "-+-" + "-" * longest_user + "-+"))
            else:
                puts(colored.yellow("+--------+-" + "-" * longest_host + "-+-" + "-" * longest_note + "-+"))

        # Hang until we get a keypress
        key = readchar.readkey()

        if key == readchar.key.UP or key == 'k':
            # Ensure the new selection would be valid
            if (selected_target - 1) >= 0:
                selected_target -= 1

            # Empty the number buffer
            number_buffer = []

        elif key == readchar.key.DOWN or key == 'j':
            # Ensure the new selection would be valid
            if (selected_target + 1) <= (num_targets - 1):
                selected_target += 1

            # Empty the number buffer
            number_buffer = []

        elif key == 'g':
            # Go to top
            selected_target = 0

            # Empty the number buffer
            number_buffer = []

        elif key == 'G':
            # Go to bottom
            selected_target = num_targets - 1

            # Empty the number buffer
            number_buffer = []

        elif key == 'q':
            if 'host' in target:
                # Go to main menu
                config = json.loads(resources.user.read(config_name))
                display_menu(config['targets'])

               # Empty the number buffer
                number_buffer = []
            else:
                exit(0)

        elif key == readchar.key.ENTER:
            # For cleanliness clear the screen
            call(['tput', 'clear'])

            target = targets[selected_target]
            # Host to connect
            if 'host' in target:

                # Check if there is a custom command for this target
                if 'command' in target.keys():
                    command = target['command']
                else:
                    command = 'ssh'

                # Arguments to the child process should start with the name of the command being run
                args = [command] + target.get('options', []) + [target['host']]

                try:
                    # After this line, ssh will replace the python process
                    os.execvp(command, args)
                except FileNotFoundError:
                    sys.exit('Command not found: {commandname}'.format(commandname=command))

            # Group of hosts
            else:
                display_menu(target[list(target.keys())[0]])

        elif key == 'h':
            display_help()

        elif key == readchar.key.CTRL_C:
            exit(0)

        # Check if key is a number
        elif key in map(lambda x: str(x), range(10)):
            requested_target = int(key)

            # Check if there are any previously entered numbers, and append if less than one second has gone by
            if round(time.time()) - number_last <= 1:
                number_buffer += key
                requested_target = int(''.join(number_buffer))
                # If the new target is invalid, just keep the previously selected target instead
                if requested_target >= num_targets:
                    requested_target = selected_target
            else:
                number_buffer = [key]

            number_last = round(time.time())

            # Ensure the new selection would be valid
            if requested_target >= num_targets:
                requested_target = num_targets - 1

            selected_target = requested_target


main()
