#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

"""

from lvm4py import LVM
import os
from subprocess import call, check_output
from datetime import datetime, timedelta
import time
import re
import sys
import argparse

lvm = LVM()
token = time.time()
now = datetime.now()

parser = argparse.ArgumentParser(description='Expandir disco automaticamente')
parser.add_argument('-m','--ponto_de_montagem', type=str, metavar='', required=True, help='Informar o ponto de montagem')
parser.add_argument('-q','--qtd', type=int, metavar='', required=True, help='Quantidade a ser expandida')
args = parser.parse_args()

def is_mp(ponto_de_montagem, qtd):
    if os.path.ismount(ponto_de_montagem) == True:
        create_disk(ponto_de_montagem)
        expander_lvm(ponto_de_montagem,qtd)
    else:
        sys.exit(1)
        
def discoreved_disks():
    os.system('for i in /sys/class/scsi_host/*; do echo "- - -" > $i/scan; done') 
    os.system("fdisk -l | grep \"Disk /dev/sd\" | awk '{print $2}' | sed \"s/\://\" > /tmp/expander_old.txt")
    token_file()
    
def token_file():
    os.system("echo \" "+str(token)+" \" > /tmp/arquivo.txt")

def create_disk(ponto_de_montagem):
    get_sdx = check_output("diff /tmp/expander_new.txt /tmp/expander_old.txt | grep sd | awk '{print $2}'", shell=True).rstrip()
    device = check_output("grep " + ponto_de_montagem + " /etc/fstab | awk '{print $1}'", shell=True)
    vgs = re.split(r'[/,-]', device)
    if 'mapper' in vgs :
        vg_name = vgs[3]
        os.system("echo -e \"o\nn\np\n1\n\n\nt\n8e\nw\" | fdisk "+get_sdx)
        get_sdx_partition = get_sdx + '1'
        os.system("pvcreate "+get_sdx_partition)
        os.system("vgextend "+vg_name+" "+get_sdx_partition)
    else:
        sys.exit(2)

def expander_lvm(ponto_de_montagem, qtd):
    dataatual = now
    device = check_output("grep \" " + ponto_de_montagem + " \" /etc/fstab | awk '{print $1}'", shell=True)
    vgs = re.split(r'[/,-]', device)
    vg_name = vgs[3]
    if call("vgs | grep "+ vg_name,stdout=None,shell=True) == 0:
        vg = lvm.get_vg(vg_name)
        if int(qtd) < vg.free('G'):
            if os.path.exists('/etc/lvm/relatorio.txt'):
                arq = open('/etc/lvm/relatorio.txt','r')
                texto = arq.readlines()
                for linha in texto:
                    linha = linha.strip()
                    vgdata = re.split('/', linha)
                    if vg_name == vgdata[0]:
                        datalvextend = datetime.strptime(vgdata[1], '%Y-%m-%d %H:%M:%S.%f')
                        meia_hora_depois = datalvextend  + timedelta(minutes = 1440)
                    else:
                        sys.exit(0)        
                if dataatual >= meia_hora_depois:
                    os.system("lvextend -L +" + str(qtd) + "g " + device)
                    os.system("resize2fs " + device)
                    arq = open('/etc/lvm/relatorio.txt','a')
                    data = str(now) 
                    texto = []
                    texto.append(vg_name + "/" + data + "\n")
                    arq.writelines(texto)
                    arq.close()
                    sys.exit("VG expanded")
                else:
                    sys.exit('Expandir somente daqui 24 horas!')
            else:
                os.system("lvextend -L +" + str(qtd) + "g " + device)
                os.system("resize2fs " + device)
                arq = open('/etc/lvm/relatorio.txt','w')
                arq = open('/etc/lvm/relatorio.txt','r')
                texto = arq.readlines()
                arq = open('/etc/lvm/relatorio.txt','a')
                data = str(now) 
                texto = []
                texto.append(vg_name + "/" + data + "\n")
                arq.writelines(texto)
                arq.close()
        else:
            print('size larger than expected')
            discoreved_disks()
            create_disk(ponto_de_montagem)
            os.system("lvextend -L +" + str(qtd) + "g " + device)
            os.system("resize2fs -p " + device)
    else:
        sys.exit(3)

def expander_disk(ponto_de_montagem, qtd):
    try:
        if (qtd <= 100):
            is_mp(ponto_de_montagem,qtd)
        else:
            sys.exit('finalized')
    except Exception as erro:
        print(erro)

if __name__ == '__main__':
    expander_disk(args.ponto_de_montagem, args.qtd)
