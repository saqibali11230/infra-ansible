ssh-config role
=========

This is a common role that should be run on all systems. As such, it is made a metadependancy to the common role.

Purpose
-----------

This role provisions a system with neccessary user public keys to allow ansible
executions from a users home directory on the ansible host. The provisiong also
includes a modification to AuthorizedKeysFile in sshd config, and, if changed,
sshd is reloaded.

SSH Key Generation Requirements
------------
- token type is RSA
- token length is 4096
- token name is a users Active Directory sAMAccountName
- do not set a passphrase

Command
---
```
ssh-keygen -t rsa -b 4096
```
