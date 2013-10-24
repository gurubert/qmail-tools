#!/usr/bin/python

#
# (c) 2004 Epigenomics AG
#
# written by Robert Sander <robert.sander@epigenomics.com>
#
# released under GPL
#
#
# This script collects nearly all possible
# local parts for emails on a qmail system.
#
# It is for use with the RECIPIENTS extension
# from http://www.fehcom.de/qmail/qmail.html
#
# It reads users from the system password database,
# /var/qmail/users/assign, aliases from /etc/aliases (fastforward)
# and /var/qmail/alias. It also reads virtual users for domains
# managed by vpopmail, if they exist.
#
# It does not read users for other virtual domains.
#
# Use at your own risk.
#

import pwd, commands, os, os.path, sys

locals = map(lambda x: x.strip(), open("/var/qmail/control/locals").readlines())

def execute(command):
    rc, output = commands.getstatusoutput(command)
    if rc:
        print output
        sys.exit(rc)
    else:
        return output

def process_aliases(aliaslist):
    output = []
    for alias in aliaslist:
        if alias[-8:] == "-default":
            if alias[:-8] in output:
                continue
            if alias[-15:] == "-accept-default" or alias[-15:] == "-reject-default" or alias[-15:] == "-return-default":
                if alias[:-15] in output:
                    continue
            alias = alias[:-8]
        if alias[-6:] == "-owner":
            if alias[:-6] in output:
                continue
        output.append(alias)
    return output

def get_users():
    output = []
    for user in pwd.getpwall():
        try:
            st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime = os.stat(user[5])
            if st_uid and st_uid == user[2] and user[0] == user[0].lower():
                output = output + map(lambda x: "%s@%s" % (user[0], x), locals)
        except OSError:
            pass
    return output

def get_users_assign():
    output = []
    try:
        assign = open("/var/qmail/users/assign").readlines()
        for line in assign:
            if line[0] == "=":
                local, user, uid, gid, homedir, dash, ext, rem = line.strip().split(":")
                output = output + map(lambda x: "%s@%s" % (local[1:], x), locals)
    except IOError:
        pass
    return output

def get_alias():
    input = execute("/bin/ls /var/qmail/alias/.qmail-* | cut -f 2- -d - | tr [:] [.]").split("\n")
    input.sort()
    return process_aliases(input)

def get_virtualdomains():
    output = []
    virtualdomains = {}
    virtualaliases = {}
    virtualdefault = {}
    if not os.path.exists("/var/qmail/control/virtualdomains"):
        return output
    for virtualdomain in open("/var/qmail/control/virtualdomains").readlines():
        domain, user = virtualdomain.strip().split(":")
        virtualdomains[domain] = user
        uservdomain = None
        if not virtualaliases.has_key(user):
            virtualaliases[user] = []
            virtualdefault[user] = []

            parts = user.split('-')
            if len(parts) > 1:
                userpart = parts[0]
                extension = "-".join(parts[1:])
                valiases = execute("ls -a /var/qmail/alias/.qmail-%s-%s-* 2>/dev/null | cut -f 2- -d - | tr [:] [.]" % (
                                                                                                                         userpart,
                                                                                                                         extension)).split("\n")
                if valiases == ['']:
                    valiases = execute("ls -a ~%s/.qmail-%s-* 2>/dev/null | cut -f 2- -d - | tr [:] [.]" % ( 
                                                                                                             userpart,
                                                                                                             extension)).split("\n")
                    uservdomain = 1
            else:
                extension = ""
                valiases = execute("ls -a /var/qmail/alias/.qmail-%s-* 2>/dev/null | cut -f 2- -d - | tr [:] [.]" % ( user )).split("\n")
                if valiases == ['']:
                    valiases = execute("ls -a ~%s/.qmail-* 2>/dev/null | cut -f 2- -d - | tr [:] [.]" % ( user )).split("\n")
                    uservdomain = 1
            # print uservdomain, valiases, process_aliases(valiases)
            for valias in process_aliases(valiases):
                if uservdomain:
                    realvalias = valias[len(extension)+1:]
                else:
                    realvalias = valias[len(user)+1:]
                # print host, vdomain, user, extension, valias, realvalias, len(realvalias)
                if realvalias == "":
                    if uservdomain:
                        if extension:
                            content = execute("cat ~%s/.qmail-%s-default 2>/dev/null" % ( userpart,
                                                                                          extension)).split("\n")
                        else:
                            content = execute("cat ~%s/.qmail-default 2>/dev/null" % ( user )).split("\n")
                    else:
                        content = execute("cat /var/qmail/alias/.qmail-%s-default 2>/dev/null" % ( user )).split("\n")
                    # print content
                    if '|/var/qmail/bin/forward $DEFAULT' in content:
                        virtualdefault[user].append(domain)
                    else:
                        # TODO: seems to accept all mail, what shall we do?
                        pass
                else:
                    virtualaliases[user].append(realvalias)
        else:
            virtualdefault[user].append(domain)
    for vdomain in virtualdomains.keys():
        output.extend(map(lambda x: x + "@" + vdomain, virtualaliases[virtualdomains[vdomain]]))
    return output

aliases = get_users() + get_users_assign() + get_alias() + get_virtualdomains()

print "\n".join(aliases)
