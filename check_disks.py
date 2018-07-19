#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

"""

import os

def compare_disk():
    os.system("fdisk -l | grep \"Disk /dev/sd\" | awk '{print $2}' | sed \"s/\://\" > /tmp/expander_new.txt")

if __name__ == '__main__':
    compare_disk()