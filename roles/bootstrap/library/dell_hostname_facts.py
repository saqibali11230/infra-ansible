#!/usr/bin/env python3

__metaclass__ = type

DOCUMENTATION = r'''
---
module: vmware_hostname_facts

short_description: Query vSphere for VM's prospective hostname

version_added: "1.0.0"

description: Ansible operation is entirely data driven. Therefore,
    programmatic access to the data as a structure is required. However,
    some configuration must be done early, at installation time. Such a
    node does not have enough configuration yet to be managed, and
    therefore must use some unique identifier to access enough data to
    bootstrap automated configuration. In Ansible, hostnames are the
    highest-level identifiers to information about hosts.  Therefore, an
    attempt can be to determine the hostname.  For VMware hosts, a query
    can be made to vSphere. For Dell hardware hosts, the inventory can be
    iterated to find the service tag. For hosts which set the hostname
    explicitely during installer execution, the initial hostname can be
    examined to determine if it differs from a default hostname. Failure of
    all of these strategies is an error condition.

author:
    - Amelia Marie Collins <acollins@mutualink.net>
'''

EXAMPLES = r'''
- name: Look up prospective hostname in VMware
  vmware_hostname_facts:
      user: 'username'
      password: 'password'

- name: Display VMware hostname
  debug:
      msg: VMware hostname was {{ prospective_hostname }}
'''

RETURN = r'''
ansible_facts:
  description: Facts to add to ansible_facts.
  returned: always
  type: dict
  contains:
    prospective_hostname:
      description: Prospective hostname from VMware
      type: str
      returned: always
      sample: 'wfr-auto-example-1'
'''

from ansible.module_utils.basic import AnsibleModule
import sys
import argparse
import getpass
import re
import subprocess
from pyVim import connect

def get_mangled_vmware_uuid():
    proc = subprocess.Popen(['/usr/sbin/dmidecode'], stdout=subprocess.PIPE)
    (out, err) = proc.communicate()
    dmidecode = out.decode('UTF-8').split('\n')

    in_block = False
    for line in dmidecode:
        # Skip lines up to system info block
        if not in_block and not re.match(r'^System Information', line):
            continue
        in_block = True

        # Reached end of block?
        if re.match(r'^$', line):
            break

        # Look for UUID line inside block
        if re.match(r'^\tUUID: ', line):
            return line.split(' ')[1]

    # Couldn't find UUID in system information block
    return None

def unmangle_vmware_uuid(uuid):
    # Under VMware, the UUID returned by dmidecode is mangled and does not
    # correspond directly to the true VMware UUID. The reason for this is
    # unknown. Specifically, the first three hyphen-separated fields are
    # byte-reversed. For example, if dmidecode returns
    #     8bd41842-b85c-7fc5-3fc5-5b7c43f83d21
    # then the UUID in VMware is
    #     4218d48b-5cb8-c57f-3fc5-5b7c43f83d21
    # Because ASCII encoding of base 16 representations represents each
    # nybble (4 bits) with a character, bytes are represented by two
    # characters and must be manipulated as a pair.
    return '-'.join([
        ''.join([uuid[6:8], uuid[4:6], uuid[2:4], uuid[0:2]]),
        ''.join([uuid[11:13], uuid[9:11]]),
        ''.join([uuid[16:18], uuid[14:16]]),
        uuid[19:] # the final two fields and their joining hyphen, unaltered
    ])

def run_module():
    # What module accepts
    module_args = dict()

    # What module returns
    result = {
        'ansible_facts': {
            'changed': False,
        }
    }

    # Build on AnsibleModule
    module = AnsibleModule(
        argument_spec = module_args,
        supports_check_mode = True
    )

    # In check_mode, only return default values
    if module.check_mode:
        module.exit_json(**result)

    hostvars = module.params['hostvars']

    # Hostname set by installer? Use it
    if hostvars['ansible_hostname'] != 'ubuntu':
        result['ansible_facts']['prospective_hostname'] = hostvars['ansible_hostname']
        module.exit_json(**result)

    # VMware VM? Query vSphere for VM hostname
    if hostvars['ansible_system_vendor'] == 'VMware, Inc.':
        vsphere_client = connect.SmartConnectNoSSL(
                host='masterplan.corp.mutualink.net',
                port=options.port,
                user=options.user,
                pwd=password).RetrieveContent()
        vm = vsphere_client.searchIndex.FindByUuid(
                uuid=unmangle_vmware_uuid(get_mangled_vmware_uuid()),
                vmSearch=True)

        if vm:
            result['ansible_facts'] = { 'prospective_hostname': vm.name }

        module.exit_json(**result)

    # TODO: Hostname lookup by service tag for Dell Harware

    # Failure to determine a hostname conclusively during
    # bootstrap config is an error condition and continuing
    # is impossible


def main():
    run_module()


if __name__ == '__main__':
    main()

